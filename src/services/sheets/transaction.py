"""
Atomic transaction support for Google Sheets operations.

When creating an order, data is written to multiple sheets:
- Designer DATA
- Clients DATA
- GENERAL

If any write fails, all previously written data is rolled back
using operation_id to identify and delete rows.
"""
import uuid
from dataclasses import dataclass, field
from typing import List, Any, Optional
from enum import Enum
from loguru import logger

from src.services.sheets.client import SheetsClient, get_sheets_client
from src.config.sheets_config import get_sheet_config


class TransactionError(Exception):
    """Raised when transaction fails and rollback is triggered."""
    pass


class OperationStatus(Enum):
    """Status of a single operation within transaction."""
    PENDING = "pending"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class SheetOperation:
    """Single write operation to a sheet."""
    sheet_key: str          # Key from SHEETS_CONFIG (e.g., "designer_data")
    data: List[Any]         # Data for data columns
    operation_id: str       # UUID for this operation
    status: OperationStatus = OperationStatus.PENDING
    row_number: Optional[int] = None  # Set after successful write


@dataclass
class TransactionResult:
    """Result of a transaction."""
    success: bool
    operation_id: str
    committed_operations: List[SheetOperation] = field(default_factory=list)
    failed_operation: Optional[SheetOperation] = None
    error: Optional[str] = None


class SheetTransaction:
    """
    Atomic transaction for writing to multiple sheets.

    Usage:
        async with SheetTransaction() as tx:
            tx.add_row("designer_data", designer_row_data)
            tx.add_row("clients_data", client_row_data)
            tx.add_row("general", general_row_data)
            result = await tx.commit()

    If any write fails, all previous writes are rolled back.
    """

    def __init__(self, client: Optional[SheetsClient] = None):
        """
        Initialize transaction.

        Args:
            client: Optional SheetsClient instance.
                   If not provided, uses singleton.
        """
        self._client = client or get_sheets_client()
        self._operations: List[SheetOperation] = []
        self._operation_id: str = str(uuid.uuid4())
        self._committed: bool = False

    @property
    def operation_id(self) -> str:
        """Get the operation ID for this transaction."""
        return self._operation_id

    def add_row(self, sheet_key: str, data: List[Any]) -> None:
        """
        Add a row write operation to the transaction.

        Args:
            sheet_key: Key from SHEETS_CONFIG (e.g., "designer_data")
            data: List of values for data columns

        Raises:
            ValueError: If transaction already committed
        """
        if self._committed:
            raise ValueError("Cannot add operations to committed transaction")

        operation = SheetOperation(
            sheet_key=sheet_key,
            data=data,
            operation_id=self._operation_id
        )
        self._operations.append(operation)
        logger.debug(f"Added operation to {sheet_key}, operation_id={self._operation_id}")

    async def commit(self) -> TransactionResult:
        """
        Execute all operations atomically.

        Returns:
            TransactionResult with success status and details

        Raises:
            TransactionError: If commit fails after rollback
        """
        if self._committed:
            raise ValueError("Transaction already committed")

        if not self._operations:
            logger.warning("Empty transaction, nothing to commit")
            return TransactionResult(
                success=True,
                operation_id=self._operation_id
            )

        committed_ops: List[SheetOperation] = []
        failed_op: Optional[SheetOperation] = None
        error_msg: Optional[str] = None

        try:
            # Execute operations one by one
            for op in self._operations:
                try:
                    # Find empty row and write
                    row_num = await self._client.write_row(
                        sheet_key=op.sheet_key,
                        operation_id=op.operation_id,
                        data=op.data
                    )
                    op.row_number = row_num
                    op.status = OperationStatus.COMMITTED
                    committed_ops.append(op)

                    logger.info(
                        f"Committed to {op.sheet_key}, "
                        f"row={row_num}, operation_id={op.operation_id}"
                    )

                except Exception as e:
                    op.status = OperationStatus.FAILED
                    failed_op = op
                    error_msg = str(e)
                    logger.error(f"Failed to write to {op.sheet_key}: {e}")
                    raise

            self._committed = True
            return TransactionResult(
                success=True,
                operation_id=self._operation_id,
                committed_operations=committed_ops
            )

        except Exception as e:
            # Rollback all committed operations
            logger.warning(f"Rolling back transaction {self._operation_id}")
            await self._rollback(committed_ops)

            self._committed = True  # Mark as done (failed)

            return TransactionResult(
                success=False,
                operation_id=self._operation_id,
                committed_operations=[
                    op for op in committed_ops
                    if op.status == OperationStatus.ROLLED_BACK
                ],
                failed_operation=failed_op,
                error=error_msg
            )

    async def _rollback(self, operations: List[SheetOperation]) -> None:
        """
        Rollback committed operations by clearing their rows.

        Args:
            operations: List of operations to rollback
        """
        for op in operations:
            try:
                success = await self._client.delete_row_by_operation_id(
                    sheet_key=op.sheet_key,
                    operation_id=op.operation_id
                )
                if success:
                    op.status = OperationStatus.ROLLED_BACK
                    logger.info(f"Rolled back {op.sheet_key}, row={op.row_number}")
                else:
                    logger.error(f"Failed to rollback {op.sheet_key}, row not found")
            except Exception as e:
                logger.error(f"Error during rollback of {op.sheet_key}: {e}")

    async def __aenter__(self) -> "SheetTransaction":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        Async context manager exit.

        If exception occurred and transaction not committed, rollback.
        """
        if exc_type is not None and not self._committed:
            # Exception occurred, rollback any committed operations
            committed = [op for op in self._operations if op.status == OperationStatus.COMMITTED]
            if committed:
                logger.warning(f"Exception in transaction, rolling back {len(committed)} ops")
                await self._rollback(committed)

        return False  # Don't suppress exceptions


async def create_order_transaction(
    designer_data: List[Any],
    client_data: List[Any],
    general_data: List[Any]
) -> TransactionResult:
    """
    Convenience function to create a full order transaction.

    Writes to all three sheets atomically:
    - Designer DATA
    - Clients DATA
    - GENERAL

    Args:
        designer_data: Row data for Designer DATA sheet
        client_data: Row data for Clients DATA sheet
        general_data: Row data for GENERAL sheet

    Returns:
        TransactionResult with operation_id and status
    """
    async with SheetTransaction() as tx:
        tx.add_row("designer_data", designer_data)
        tx.add_row("clients_data", client_data)
        tx.add_row("general", general_data)
        return await tx.commit()
