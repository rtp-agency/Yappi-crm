"""
Google Sheets async client.

Provides base operations for reading/writing to Google Sheets.
"""
import asyncio
from typing import List, Optional, Any, Dict
from concurrent.futures import ThreadPoolExecutor
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger

from src.config.settings import get_settings
from src.config.sheets_config import SheetConfig, get_sheet_config


class SheetsClient:
    """
    Async Google Sheets API client.

    Uses ThreadPoolExecutor to make sync Google API calls async.
    """

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(self):
        self._settings = get_settings()
        self._executor = ThreadPoolExecutor(max_workers=3)
        self._service = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Google Sheets API client."""
        if self._initialized:
            return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self._init_service)
        self._initialized = True
        logger.info("Google Sheets client initialized")

    def _init_service(self) -> None:
        """Initialize Google API service (sync, runs in executor)."""
        credentials = Credentials.from_service_account_file(
            self._settings.CREDENTIALS_FILE,
            scopes=self.SCOPES
        )
        self._service = build("sheets", "v4", credentials=credentials)

    @property
    def spreadsheet_id(self) -> str:
        """Get spreadsheet ID from settings."""
        return self._settings.SPREADSHEET_ID

    # ========================================================================
    # LOW-LEVEL OPERATIONS
    # ========================================================================

    async def _run_sync(self, func, *args, **kwargs) -> Any:
        """Run synchronous function in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: func(*args, **kwargs)
        )

    async def get_range(self, sheet_name: str, range_str: str) -> List[List[Any]]:
        """
        Read values from a range.

        Args:
            sheet_name: Name of the sheet
            range_str: Range in A1 notation (e.g., "A1:K100" or "F:K")

        Returns:
            2D list of values
        """
        await self.initialize()

        full_range = f"'{sheet_name}'!{range_str}"

        def _read():
            result = self._service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=full_range,
                valueRenderOption="UNFORMATTED_VALUE",
                dateTimeRenderOption="FORMATTED_STRING"
            ).execute()
            return result.get("values", [])

        try:
            return await self._run_sync(_read)
        except HttpError as e:
            logger.error(f"Error reading range {full_range}: {e}")
            raise

    async def append_row(
        self,
        sheet_name: str,
        row_data: List[Any],
        range_str: str
    ) -> Dict[str, Any]:
        """
        Append a row to the sheet.

        Args:
            sheet_name: Name of the sheet
            row_data: List of values for the row
            range_str: Range to append to (e.g., "A:K")

        Returns:
            API response with updates info
        """
        await self.initialize()

        full_range = f"'{sheet_name}'!{range_str}"

        def _append():
            body = {"values": [row_data]}
            return self._service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=full_range,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()

        try:
            result = await self._run_sync(_append)
            logger.debug(f"Appended row to {full_range}")
            return result
        except HttpError as e:
            logger.error(f"Error appending to {full_range}: {e}")
            raise

    async def update_range(
        self,
        sheet_name: str,
        range_str: str,
        values: List[List[Any]]
    ) -> Dict[str, Any]:
        """
        Update values in a specific range.

        Args:
            sheet_name: Name of the sheet
            range_str: Range in A1 notation (e.g., "A22:K22")
            values: 2D list of values

        Returns:
            API response
        """
        await self.initialize()

        full_range = f"'{sheet_name}'!{range_str}"

        def _update():
            body = {"values": values}
            return self._service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=full_range,
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()

        try:
            result = await self._run_sync(_update)
            logger.debug(f"Updated range {full_range}")
            return result
        except HttpError as e:
            logger.error(f"Error updating {full_range}: {e}")
            raise

    async def batch_update(
        self,
        data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Batch update multiple ranges at once.

        Args:
            data: List of dicts with 'range' and 'values' keys
                  e.g., [{"range": "Sheet!A1:B2", "values": [[1,2],[3,4]]}]

        Returns:
            API response
        """
        await self.initialize()

        def _batch():
            body = {
                "valueInputOption": "USER_ENTERED",
                "data": data
            }
            return self._service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            ).execute()

        try:
            result = await self._run_sync(_batch)
            logger.debug(f"Batch updated {len(data)} ranges")
            return result
        except HttpError as e:
            logger.error(f"Error in batch update: {e}")
            raise

    async def clear_range(self, sheet_name: str, range_str: str) -> None:
        """Clear values in a range."""
        await self.initialize()

        full_range = f"'{sheet_name}'!{range_str}"

        def _clear():
            return self._service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=full_range,
                body={}
            ).execute()

        try:
            await self._run_sync(_clear)
            logger.debug(f"Cleared range {full_range}")
        except HttpError as e:
            logger.error(f"Error clearing {full_range}: {e}")
            raise

    async def get_sheet_id(self, sheet_name: str) -> Optional[int]:
        """
        Get the sheet ID (gid) by sheet name.

        Args:
            sheet_name: Name of the sheet

        Returns:
            Sheet ID (integer) or None if not found
        """
        await self.initialize()

        def _get_metadata():
            return self._service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id,
                fields="sheets.properties"
            ).execute()

        try:
            result = await self._run_sync(_get_metadata)
            for sheet in result.get("sheets", []):
                props = sheet.get("properties", {})
                if props.get("title") == sheet_name:
                    return props.get("sheetId")
            return None
        except HttpError as e:
            logger.error(f"Error getting sheet ID for {sheet_name}: {e}")
            return None

    async def format_cells(
        self,
        sheet_name: str,
        row_number: int,
        start_col: str,
        end_col: str,
        font_family: str = "Roboto",
        font_size: int = 11,
        font_color: tuple = (0, 0, 0),  # RGB black
        horizontal_alignment: str = None  # LEFT, CENTER, RIGHT
    ) -> bool:
        """
        Format cells with specified font settings.

        Args:
            sheet_name: Name of the sheet
            row_number: Row to format (1-based)
            start_col: Start column letter (e.g., 'A')
            end_col: End column letter (e.g., 'K')
            font_family: Font name (default: Roboto)
            font_size: Font size (default: 11)
            font_color: RGB tuple (default: black)
            horizontal_alignment: LEFT, CENTER, RIGHT (default: None - no change)

        Returns:
            True if successful
        """
        await self.initialize()

        sheet_id = await self.get_sheet_id(sheet_name)
        if sheet_id is None:
            logger.error(f"Sheet not found: {sheet_name}")
            return False

        # Convert column letters to indices (0-based)
        start_col_index = ord(start_col.upper()) - ord('A')
        end_col_index = ord(end_col.upper()) - ord('A') + 1  # +1 because end is exclusive

        def _format():
            cell_format = {
                "textFormat": {
                    "fontFamily": font_family,
                    "fontSize": font_size,
                    "foregroundColor": {
                        "red": font_color[0],
                        "green": font_color[1],
                        "blue": font_color[2]
                    }
                }
            }

            fields = "userEnteredFormat.textFormat"

            # Add horizontal alignment if specified
            if horizontal_alignment:
                cell_format["horizontalAlignment"] = horizontal_alignment.upper()
                fields += ",userEnteredFormat.horizontalAlignment"

            request = {
                "requests": [{
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": row_number - 1,  # 0-based
                            "endRowIndex": row_number,
                            "startColumnIndex": start_col_index,
                            "endColumnIndex": end_col_index
                        },
                        "cell": {
                            "userEnteredFormat": cell_format
                        },
                        "fields": fields
                    }
                }]
            }
            return self._service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=request
            ).execute()

        try:
            await self._run_sync(_format)
            logger.debug(f"Formatted row {row_number} in {sheet_name}")
            return True
        except HttpError as e:
            logger.error(f"Error formatting cells: {e}")
            return False

    # ========================================================================
    # HIGH-LEVEL OPERATIONS (SHEET CONFIG AWARE)
    # ========================================================================

    async def get_first_empty_row(self, sheet_key: str) -> int:
        """
        Find the first empty row in the data columns range.

        Uses sheet config to determine:
        - start_row: minimum row to consider
        - data_columns: columns to check for emptiness
        - skip_rows: rows to skip (never write to)

        Logic:
        1. Read all data from data_columns starting from start_row
        2. Find first row where ALL data columns are empty
        3. Skip rows from skip_rows list
        4. Return row number (1-based)

        Args:
            sheet_key: Key from SHEETS_CONFIG (e.g., "designer_data")

        Returns:
            Row number (1-based) of the first empty row
        """
        config = get_sheet_config(sheet_key)

        # Read from start_row to find existing data
        # Read up to 500 rows (enough for most cases, avoids timeout)
        max_row = config.start_row + 500
        read_range = f"{config.data_start_col}{config.start_row}:{config.data_end_col}{max_row}"

        try:
            data = await self.get_range(config.name, read_range)
        except HttpError:
            # If no data exists, start from start_row (but check skip_rows)
            result_row = config.start_row
            while result_row in config.skip_rows:
                result_row += 1
            return result_row

        if not data:
            result_row = config.start_row
            while result_row in config.skip_rows:
                result_row += 1
            return result_row

        # Find first completely empty row (skipping skip_rows)
        for i, row in enumerate(data):
            current_row = config.start_row + i

            # Skip protected rows
            if current_row in config.skip_rows:
                continue

            # Check if row is completely empty
            is_empty = not row or all(
                cell == "" or cell is None
                for cell in row
            )
            if is_empty:
                return current_row

        # All rows have data, return next row after last (but check skip_rows)
        result_row = config.start_row + len(data)
        while result_row in config.skip_rows:
            result_row += 1
        return result_row

    async def read_all_data(self, sheet_key: str) -> List[List[Any]]:
        """
        Read all data from a sheet starting from its start_row.

        Includes operation_id column (A) and data columns.

        Args:
            sheet_key: Key from SHEETS_CONFIG

        Returns:
            List of rows with data
        """
        config = get_sheet_config(sheet_key)

        # Read ID column + data columns (up to 500 rows)
        max_row = config.start_row + 500
        read_range = f"{config.id_column}{config.start_row}:{config.data_end_col}{max_row}"

        try:
            data = await self.get_range(config.name, read_range)
            # Filter out empty rows
            return [row for row in data if row and any(cell for cell in row)]
        except HttpError:
            return []

    async def write_row(
        self,
        sheet_key: str,
        operation_id: str,
        data: List[Any],
        row_number: Optional[int] = None,
        apply_formatting: bool = True
    ) -> int:
        """
        Write a row to the sheet at the first empty position.

        Writes operation_id to column A and data to data_columns.
        Respects protected columns (skips them).
        Applies default formatting (Roboto, size 11, black).

        Args:
            sheet_key: Key from SHEETS_CONFIG
            operation_id: UUID for this operation
            data: List of values for data columns
            row_number: Optional specific row to write to.
                       If None, finds first empty row.
            apply_formatting: Whether to apply font formatting (default: True)

        Returns:
            Row number where data was written
        """
        config = get_sheet_config(sheet_key)

        if row_number is None:
            row_number = await self.get_first_empty_row(sheet_key)

        # Build row with operation_id in column A
        # For Designer DATA: A=ID, B-E=empty (protected), F-K=data
        col_a_index = ord(config.id_column.upper()) - ord('A')
        data_start_index = ord(config.data_start_col.upper()) - ord('A')

        # Create full row with proper spacing
        full_row = [""] * (data_start_index + len(data))
        full_row[col_a_index] = operation_id

        # Fill data columns
        for i, value in enumerate(data):
            full_row[data_start_index + i] = value

        # Write the row
        write_range = f"{config.id_column}{row_number}:{config.data_end_col}{row_number}"

        await self.update_range(
            config.name,
            write_range,
            [full_row]
        )

        # Apply formatting
        if apply_formatting:
            # Make operation_id invisible (white text on white background)
            await self.format_cells(
                sheet_name=config.name,
                row_number=row_number,
                start_col=config.id_column,
                end_col=config.id_column,
                font_family="Roboto",
                font_size=8,
                font_color=(1, 1, 1)  # White - invisible
            )

            # Date column (F) - size 10
            await self.format_cells(
                sheet_name=config.name,
                row_number=row_number,
                start_col=config.data_start_col,
                end_col=config.data_start_col,
                font_family="Roboto",
                font_size=10,
                font_color=(0, 0, 0)
            )

            # Other data columns (G:K) - size 11
            if config.data_start_col != config.data_end_col:
                next_col = chr(ord(config.data_start_col) + 1)
                await self.format_cells(
                    sheet_name=config.name,
                    row_number=row_number,
                    start_col=next_col,
                    end_col=config.data_end_col,
                    font_family="Roboto",
                    font_size=11,
                    font_color=(0, 0, 0)
                )

        logger.info(f"Wrote row {row_number} to {config.name}, operation_id={operation_id}")
        return row_number

    async def find_row_by_operation_id(
        self,
        sheet_key: str,
        operation_id: str
    ) -> Optional[int]:
        """
        Find row number by operation_id.

        Args:
            sheet_key: Key from SHEETS_CONFIG
            operation_id: UUID to search for

        Returns:
            Row number (1-based) or None if not found
        """
        config = get_sheet_config(sheet_key)

        # Read ID column (up to 500 rows)
        max_row = config.start_row + 500
        read_range = f"{config.id_column}{config.start_row}:{config.id_column}{max_row}"

        try:
            data = await self.get_range(config.name, read_range)
        except HttpError:
            return None

        for i, row in enumerate(data):
            if row and row[0] == operation_id:
                return config.start_row + i

        return None

    async def insert_row_with_formulas(
        self,
        sheet_name: str,
        after_row: int
    ) -> bool:
        """
        Insert a new row after specified row, copying formulas from that row.

        This makes the table "grow" properly with formulas intact.

        Args:
            sheet_name: Name of the sheet
            after_row: Row number after which to insert (1-based)

        Returns:
            True if successful
        """
        await self.initialize()

        sheet_id = await self.get_sheet_id(sheet_name)
        if sheet_id is None:
            logger.error(f"Sheet not found: {sheet_name}")
            return False

        def _insert_and_copy():
            # 1. Insert a new row after the specified row
            insert_request = {
                "insertDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": after_row,  # 0-based, so after_row in 1-based = after_row in 0-based for insert
                        "endIndex": after_row + 1
                    },
                    "inheritFromBefore": True  # Copy formatting from row above
                }
            }

            # 2. Copy everything (format + formulas) from the row above to the new row
            copy_request = {
                "copyPaste": {
                    "source": {
                        "sheetId": sheet_id,
                        "startRowIndex": after_row - 1,  # Source row (0-based)
                        "endRowIndex": after_row,
                        "startColumnIndex": 0,
                        "endColumnIndex": 26  # A to Z
                    },
                    "destination": {
                        "sheetId": sheet_id,
                        "startRowIndex": after_row,  # New row (0-based)
                        "endRowIndex": after_row + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 26
                    },
                    "pasteType": "PASTE_NORMAL",  # Copy format + formulas + values
                    "pasteOrientation": "NORMAL"
                }
            }

            return self._service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": [insert_request, copy_request]}
            ).execute()

        try:
            await self._run_sync(_insert_and_copy)
            logger.debug(f"Inserted row after {after_row} in {sheet_name} with formulas")
            return True
        except HttpError as e:
            logger.error(f"Error inserting row: {e}")
            return False

    async def get_last_data_row(self, sheet_name: str, check_column: str, start_row: int) -> int:
        """
        Find the last row with data in a specific column.

        Args:
            sheet_name: Name of the sheet
            check_column: Column to check for data (e.g., 'F')
            start_row: Row to start checking from

        Returns:
            Last row number with data, or start_row - 1 if no data
        """
        max_row = start_row + 500
        read_range = f"{check_column}{start_row}:{check_column}{max_row}"

        try:
            data = await self.get_range(sheet_name, read_range)
        except HttpError:
            return start_row - 1

        last_row = start_row - 1
        for i, row in enumerate(data):
            if row and row[0]:  # Has data
                last_row = start_row + i

        return last_row

    async def write_row_expanding_table(
        self,
        sheet_key: str,
        operation_id: str,
        data: List[Any]
    ) -> int:
        """
        Write a row by inserting a new row and copying formulas from above.

        This method:
        1. Finds the last row with data
        2. Inserts a new row after it (copying formulas)
        3. Writes the data to that new row

        Use this for sheets where formulas need to be preserved (like Расходы).

        Args:
            sheet_key: Key from SHEETS_CONFIG
            operation_id: UUID for this operation
            data: List of values for data columns

        Returns:
            Row number where data was written
        """
        config = get_sheet_config(sheet_key)

        # Find last row with data (check first data column)
        last_row = await self.get_last_data_row(
            config.name,
            config.data_start_col,
            config.start_row
        )

        # Determine source row for copying format and formulas
        if last_row < config.start_row:
            # No bot data yet - copy from the row before start_row
            source_row = config.start_row - 1
            new_row = config.start_row
        else:
            # Copy from last data row
            source_row = last_row
            new_row = last_row + 1

        # Insert new row and copy format + formulas from source row
        inserted = await self.insert_row_with_formulas(config.name, source_row)

        if not inserted:
            logger.warning(f"Failed to insert row, falling back to regular write")
            return await self.write_row(
                sheet_key=sheet_key,
                operation_id=operation_id,
                data=data,
                apply_formatting=True
            )

        # Write operation_id to column A
        await self.update_cell(config.name, new_row, config.id_column, operation_id)

        # Write data to data columns
        # Format is already copied from the row above via PASTE_NORMAL
        col_index = ord(config.data_start_col) - ord('A')
        for i, value in enumerate(data):
            col_letter = chr(ord('A') + col_index + i)
            await self.update_cell(config.name, new_row, col_letter, value)

        logger.info(f"Wrote row {new_row} to {config.name} (expanded table), operation_id={operation_id}")
        return new_row

    async def update_cell(
        self,
        sheet_name: str,
        row: int,
        col: str,
        value: Any
    ) -> bool:
        """
        Update a single cell value.

        Args:
            sheet_name: Name of the sheet
            row: Row number (1-based)
            col: Column letter (e.g., 'J')
            value: Value to write

        Returns:
            True if successful
        """
        cell_range = f"{col}{row}"
        try:
            await self.update_range(sheet_name, cell_range, [[value]])
            logger.debug(f"Updated cell {sheet_name}!{cell_range} = {value}")
            return True
        except HttpError as e:
            logger.error(f"Error updating cell {sheet_name}!{cell_range}: {e}")
            return False

    async def get_unique_clients(self) -> List[str]:
        """
        Get list of unique client names from "Заказчики DATA" sheet.

        Returns:
            List of unique client names
        """
        config = get_sheet_config("clients_data")

        # Read from row 9 where existing data starts
        read_start = 9
        max_row = read_start + 500
        read_range = f"G{read_start}:G{max_row}"  # Column G = client name

        try:
            data = await self.get_range(config.name, read_range)
        except HttpError:
            return []

        # Extract unique non-empty client names
        clients = set()
        for row in data:
            if row and len(row) > 0 and str(row[0]).strip():
                clients.add(str(row[0]).strip())

        return sorted(list(clients))

    async def get_unique_designers(self) -> List[str]:
        """
        Get list of unique designer names from "Дизайнер DATA" sheet.

        Returns:
            List of unique designer names
        """
        config = get_sheet_config("designer_data")

        # Read from row 15 where designer data starts
        read_start = 15
        max_row = read_start + 500
        read_range = f"G{read_start}:G{max_row}"  # Column G = designer name

        try:
            data = await self.get_range(config.name, read_range)
        except HttpError:
            return []

        # Extract unique non-empty designer names
        designers = set()
        for row in data:
            if row and len(row) > 0 and str(row[0]).strip():
                designers.add(str(row[0]).strip())

        return sorted(list(designers))

    async def get_client_orders_with_debt(
        self,
        client_name: str
    ) -> List[Dict[str, Any]]:
        """
        Get all orders for a client from "Заказчики DATA" sheet.

        Reads columns F:L where:
        - F = date
        - G = client name
        - H = status
        - I = order amount
        - J = paid amount
        - K = debt (formula: I - J)
        - L = overpaid

        Args:
            client_name: Client name to filter by

        Returns:
            List of dicts with order info, sorted by date (oldest first)
        """
        config = get_sheet_config("clients_data")

        # Read all data from the sheet
        # Note: start_row=13 is for writing NEW data, but existing data starts from row 9
        read_start = 9  # Existing data starts from row 9
        max_row = read_start + 500
        read_range = f"F{read_start}:L{max_row}"

        try:
            data = await self.get_range(config.name, read_range)
        except HttpError:
            return []

        orders = []
        for i, row in enumerate(data):
            if not row or len(row) < 2:
                continue

            # Check if this row belongs to the client
            row_client = str(row[1]).strip() if len(row) > 1 else ""
            if row_client.lower() != client_name.lower():
                continue

            # Parse row data
            date_val = row[0] if len(row) > 0 else ""
            status = row[2] if len(row) > 2 else ""
            amount = float(row[3]) if len(row) > 3 and row[3] else 0
            paid = float(row[4]) if len(row) > 4 and row[4] else 0
            debt = float(row[5]) if len(row) > 5 and row[5] else 0

            orders.append({
                "row": read_start + i,  # Use read_start (9) not config.start_row (13)
                "date": date_val,
                "client": row_client,
                "status": status,
                "amount": amount,
                "paid": paid,
                "debt": debt,
            })

        # Sort by date (oldest first for FIFO)
        # Dates are in DD.MM.YYYY format
        def parse_date(order):
            try:
                parts = str(order["date"]).split(".")
                if len(parts) == 3:
                    return (int(parts[2]), int(parts[1]), int(parts[0]))
            except (ValueError, IndexError):
                pass
            return (9999, 99, 99)  # Put unparseable dates at the end

        orders.sort(key=parse_date)
        return orders

    async def distribute_payment_fifo(
        self,
        client_name: str,
        payment_amount: float
    ) -> List[Dict[str, Any]]:
        """
        Distribute payment across client orders using FIFO (oldest first).

        Payment is ADDED to existing paid amounts (not replaced).

        Args:
            client_name: Client name
            payment_amount: Total payment amount to distribute

        Returns:
            List of updates made: [{"row": N, "old_paid": X, "new_paid": Y, "applied": Z}, ...]
        """
        config = get_sheet_config("clients_data")

        # Get orders with debt
        orders = await self.get_client_orders_with_debt(client_name)
        orders_with_debt = [o for o in orders if o["debt"] > 0]

        if not orders_with_debt:
            return []

        remaining = payment_amount
        updates = []

        for order in orders_with_debt:
            if remaining <= 0:
                break

            debt = order["debt"]
            to_apply = min(remaining, debt)

            new_paid = order["paid"] + to_apply
            remaining -= to_apply

            # Update the cell (column J = paid)
            success = await self.update_cell(
                sheet_name=config.name,
                row=order["row"],
                col="J",
                value=new_paid
            )

            if success:
                updates.append({
                    "row": order["row"],
                    "date": order["date"],
                    "amount": order["amount"],
                    "old_paid": order["paid"],
                    "new_paid": new_paid,
                    "applied": to_apply,
                    "remaining_debt": debt - to_apply
                })

        return updates

    async def delete_row_by_operation_id(
        self,
        sheet_key: str,
        operation_id: str
    ) -> bool:
        """
        Clear a row by its operation_id (doesn't delete the row, just clears values).

        Args:
            sheet_key: Key from SHEETS_CONFIG
            operation_id: UUID of the row to clear

        Returns:
            True if row was found and cleared, False otherwise
        """
        config = get_sheet_config(sheet_key)

        row_num = await self.find_row_by_operation_id(sheet_key, operation_id)
        if row_num is None:
            return False

        # Clear only bot-managed columns (A + data columns)
        clear_range = f"{config.id_column}{row_num}:{config.data_end_col}{row_num}"
        await self.clear_range(config.name, clear_range)

        logger.info(f"Cleared row {row_num} in {config.name}")
        return True

    async def expand_sum_formula_range(
        self,
        sheet_name: str,
        cell: str,
        new_end_row: int
    ) -> bool:
        """
        Expand the range in a SUM formula to include new rows.

        For example, if cell F4 has =SUM(K10:K13) and new_end_row is 14,
        it becomes =SUM(K10:K14).

        Args:
            sheet_name: Name of the sheet
            cell: Cell reference (e.g., 'F4')
            new_end_row: New end row for the range

        Returns:
            True if successful
        """
        await self.initialize()

        try:
            # Read the current formula
            data = await self.get_range(sheet_name, f"{cell}:{cell}")
            if not data or not data[0]:
                logger.warning(f"Cell {cell} is empty")
                return False

            # We need to get the formula, not the value
            # Use the get method with valueRenderOption=FORMULA
            full_range = f"'{sheet_name}'!{cell}"

            def _get_formula():
                result = self._service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=full_range,
                    valueRenderOption="FORMULA"
                ).execute()
                return result.get("values", [[]])[0]

            formula_data = await self._run_sync(_get_formula)
            if not formula_data:
                return False

            current_formula = str(formula_data[0])
            logger.debug(f"Current formula in {cell}: {current_formula}")

            # Parse and update the formula
            # Expected format: =СУММ(K10:K13) or =SUM(K10:K13)
            import re

            # Match both Russian СУММ and English SUM
            pattern = r'(=(?:СУММ|SUM)\([A-Z]+\d+:[A-Z]+)(\d+)(\))'
            match = re.match(pattern, current_formula, re.IGNORECASE)

            if not match:
                logger.warning(f"Formula doesn't match expected pattern: {current_formula}")
                return False

            # Build new formula with updated end row
            new_formula = f"{match.group(1)}{new_end_row}{match.group(3)}"
            logger.debug(f"New formula: {new_formula}")

            # Update the cell with new formula
            await self.update_range(sheet_name, cell, [[new_formula]])

            logger.info(f"Expanded formula in {sheet_name}!{cell}: {current_formula} -> {new_formula}")
            return True

        except Exception as e:
            logger.error(f"Error expanding formula in {cell}: {e}")
            return False

    async def write_pure_income(
        self,
        operation_id: str,
        date: str,
        category: str,
        amount: float
    ) -> int:
        """
        Write a row to "Чистый доход" sheet and expand F4 formula range.

        This method:
        1. Inserts a new row after the last data row (copying formulas)
        2. Writes date, category, amount to columns F, G, H
        3. Expands F4 formula range to include the new row

        Args:
            operation_id: UUID for this operation
            date: Date string (DD.MM.YYYY)
            category: Income category (e.g., "Аренда продуктов")
            amount: Income amount

        Returns:
            Row number where data was written
        """
        config = get_sheet_config("pure_income")

        # Find last row with data (start_row = 14)
        last_row = await self.get_last_data_row(
            config.name,
            config.data_start_col,  # F
            config.start_row  # Start checking from row 14
        )

        # If no bot data found, use row 13 (last existing data row) as source for copying
        if last_row < config.start_row:
            source_row = config.start_row - 1  # Row 13 - copy format from here
            new_row = config.start_row  # Row 14 - first bot data row
        else:
            source_row = last_row
            new_row = last_row + 1

        # Always insert a new row and copy format + formulas from above
        inserted = await self.insert_row_with_formulas(config.name, source_row)
        if not inserted:
            logger.warning("Failed to insert row, using write_row")
            return await self.write_row(
                sheet_key="pure_income",
                operation_id=operation_id,
                data=[date, category, amount]
            )

        # Write operation_id to column A (white text - invisible)
        await self.update_cell(config.name, new_row, "A", operation_id)

        # Write data to columns F, G, H
        # Format is already copied from the row above via PASTE_NORMAL
        await self.update_cell(config.name, new_row, "F", date)
        await self.update_cell(config.name, new_row, "G", category)
        await self.update_cell(config.name, new_row, "H", amount)

        # Expand F4 formula range to include new row
        await self.expand_sum_formula_range(config.name, "F4", new_row)

        logger.info(f"Wrote pure income to row {new_row}, operation_id={operation_id}")
        return new_row

    async def delete_pure_income_row(
        self,
        operation_id: str
    ) -> bool:
        """
        Delete a pure income row and shrink F4 formula range.

        Args:
            operation_id: UUID of the row to delete

        Returns:
            True if successful
        """
        config = get_sheet_config("pure_income")

        # Find the row
        row_num = await self.find_row_by_operation_id("pure_income", operation_id)
        if row_num is None:
            return False

        # Get the current last data row (to know what to shrink F4 to)
        last_row = await self.get_last_data_row(config.name, "F", config.start_row)

        # Actually delete the row (not just clear)
        sheet_id = await self.get_sheet_id(config.name)
        if sheet_id is None:
            return False

        def _delete_row():
            request = {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": row_num - 1,  # 0-based
                        "endIndex": row_num
                    }
                }
            }
            return self._service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": [request]}
            ).execute()

        try:
            await self._run_sync(_delete_row)

            # Shrink F4 formula range (last_row - 1 because we deleted a row)
            if last_row >= config.start_row:
                await self.expand_sum_formula_range(config.name, "F4", last_row - 1)

            logger.info(f"Deleted pure income row {row_num}")
            return True
        except HttpError as e:
            logger.error(f"Error deleting row: {e}")
            return False

    async def get_clients_with_debts(self) -> List[Dict[str, Any]]:
        """
        Get all clients with their total debts from "Заказчики DATA" sheet.

        Aggregates data by client name:
        - Total orders amount
        - Total paid
        - Total debt

        Returns:
            List of dicts sorted by debt (highest first)
        """
        config = get_sheet_config("clients_data")

        # Read data from row 9 where existing data starts
        read_start = 9
        max_row = read_start + 500
        read_range = f"G{read_start}:L{max_row}"  # G=client, I=amount, J=paid, K=debt

        try:
            data = await self.get_range(config.name, read_range)
        except HttpError:
            return []

        # Aggregate by client
        clients_data = {}
        for row in data:
            if not row or len(row) < 1:
                continue

            client_name = str(row[0]).strip() if row[0] else ""
            if not client_name:
                continue

            # Parse values (G=0, H=1, I=2, J=3, K=4, L=5)
            # Skip header rows by catching conversion errors
            try:
                amount = float(row[2]) if len(row) > 2 and row[2] else 0
                paid = float(row[3]) if len(row) > 3 and row[3] else 0
                debt = float(row[4]) if len(row) > 4 and row[4] else 0
            except (ValueError, TypeError):
                # Skip header rows or invalid data
                continue

            if client_name not in clients_data:
                clients_data[client_name] = {
                    "client": client_name,
                    "orders_count": 0,
                    "total_amount": 0,
                    "total_paid": 0,
                    "total_debt": 0
                }

            clients_data[client_name]["orders_count"] += 1
            clients_data[client_name]["total_amount"] += amount
            clients_data[client_name]["total_paid"] += paid
            clients_data[client_name]["total_debt"] += debt

        # Convert to list and sort by debt (highest first)
        result = list(clients_data.values())
        result.sort(key=lambda x: x["total_debt"], reverse=True)
        return result

    async def get_designers_with_earnings(self) -> List[Dict[str, Any]]:
        """
        Get all designers with their earnings from "Дизайнер DATA" sheet.

        Aggregates data by designer name:
        - Total orders count
        - Total order amount
        - Total designer salary (earnings)

        Returns:
            List of dicts sorted by total salary (highest first)
        """
        config = get_sheet_config("designer_data")

        # Read data from row 15 where designer data starts
        read_start = 15
        max_row = read_start + 500
        # F=date, G=designer, H=client, I=amount, J=percent, K=salary
        read_range = f"G{read_start}:K{max_row}"

        try:
            data = await self.get_range(config.name, read_range)
        except HttpError:
            return []

        # Aggregate by designer
        designers_data = {}
        for row in data:
            if not row or len(row) < 1:
                continue

            designer_name = str(row[0]).strip() if row[0] else ""
            if not designer_name:
                continue

            # Parse values (G=0, H=1, I=2, J=3, K=4)
            # Skip header rows by catching conversion errors
            try:
                amount = float(row[2]) if len(row) > 2 and row[2] else 0
                percent = float(row[3]) if len(row) > 3 and row[3] else 0
                salary = float(row[4]) if len(row) > 4 and row[4] else 0
            except (ValueError, TypeError):
                # Skip header rows or invalid data
                continue

            # Calculate designer earnings: use salary if set, otherwise amount * percent
            # If percent < 1, it's already a fraction (0.4 = 40%), otherwise divide by 100
            if salary > 0:
                earnings = salary
            elif percent > 0 and amount > 0:
                if percent < 1:
                    # Percent is already a fraction (e.g., 0.4 = 40%)
                    earnings = amount * percent
                else:
                    # Percent is a whole number (e.g., 40 = 40%)
                    earnings = amount * percent / 100
            else:
                earnings = 0

            if designer_name not in designers_data:
                designers_data[designer_name] = {
                    "designer": designer_name,
                    "orders_count": 0,
                    "total_amount": 0,
                    "total_earnings": 0
                }

            designers_data[designer_name]["orders_count"] += 1
            designers_data[designer_name]["total_amount"] += amount
            designers_data[designer_name]["total_earnings"] += earnings

        # Convert to list and sort by earnings (highest first)
        result = list(designers_data.values())
        result.sort(key=lambda x: x["total_earnings"], reverse=True)
        return result

    async def get_expenses_by_category(self) -> List[Dict[str, Any]]:
        """
        Get expenses grouped by category from "Расходы" sheet.

        Aggregates data by category:
        - Total count
        - Total amount

        Returns:
            List of dicts sorted by total amount (highest first)
        """
        config = get_sheet_config("expenses")

        # Read data from row 9 where existing data may start
        read_start = 9
        max_row = read_start + 500
        # F=date, G=category, H=amount
        read_range = f"G{read_start}:H{max_row}"

        try:
            data = await self.get_range(config.name, read_range)
        except HttpError:
            return []

        # Aggregate by category
        categories_data = {}
        for row in data:
            if not row or len(row) < 1:
                continue

            category = str(row[0]).strip() if row[0] else ""
            if not category:
                continue

            # Parse amount (G=0, H=1)
            # Skip header rows by catching conversion errors
            try:
                amount = float(row[1]) if len(row) > 1 and row[1] else 0
            except (ValueError, TypeError):
                # Skip header rows or invalid data
                continue

            if category not in categories_data:
                categories_data[category] = {
                    "category": category,
                    "count": 0,
                    "total_amount": 0
                }

            categories_data[category]["count"] += 1
            categories_data[category]["total_amount"] += amount

        # Convert to list and sort by amount (highest first)
        result = list(categories_data.values())
        result.sort(key=lambda x: x["total_amount"], reverse=True)
        return result

    async def get_total_expenses(self) -> float:
        """
        Get total expenses from "Расходы" sheet cell F4.

        F4 contains formula =СУММ(K12:K15) which includes:
        - Manual expenses (column H)
        - Designer payments (column J)

        Returns:
            Total expenses amount
        """
        try:
            data = await self.get_range("Расходы", "F4:F4")
            if data and data[0] and data[0][0]:
                return float(data[0][0])
        except (HttpError, ValueError, TypeError, IndexError):
            pass
        return 0.0

    async def get_designer_payments(self) -> List[Dict[str, Any]]:
        """
        Get designer payments from "Расходы" sheet columns I:J starting from row 12.

        I = Designer name (formula)
        J = Payment amount (formula)

        Returns:
            List of dicts with designer name and payment amount
        """
        try:
            # Read I:J starting from row 12
            data = await self.get_range("Расходы", "I12:J100")

            payments = []
            for row in data:
                if not row or len(row) < 2:
                    continue

                designer = str(row[0]).strip() if row[0] else ""
                if not designer:
                    continue

                try:
                    amount = float(row[1]) if row[1] else 0.0
                except (ValueError, TypeError):
                    amount = 0.0

                if amount > 0:
                    payments.append({
                        "designer": designer,
                        "amount": amount
                    })

            return payments
        except HttpError:
            return []

    async def get_total_designer_payments(self) -> float:
        """
        Get total designer payments sum.

        Returns:
            Total sum of designer payments
        """
        payments = await self.get_designer_payments()
        return sum(p["amount"] for p in payments)

    async def get_debtors(self) -> List[Dict[str, Any]]:
        """
        Get clients with debt > 0.

        Returns:
            List of dicts with client name and debt, sorted by debt (highest first)
        """
        clients = await self.get_clients_with_debts()
        return [c for c in clients if c["total_debt"] > 0]

    async def get_whitelist_clients(self) -> List[str]:
        """
        Get list of clients in whitelist from "Категории" sheet.

        Returns:
            List of client names in whitelist
        """
        config = get_sheet_config("categories")

        # Read from row 2 where data starts
        read_start = 2
        max_row = read_start + 500
        # B=type, C=name, D=status
        read_range = f"B{read_start}:D{max_row}"

        try:
            data = await self.get_range(config.name, read_range)
        except HttpError:
            return []

        whitelist = []
        for row in data:
            if not row or len(row) < 3:
                continue

            item_type = str(row[0]).strip().lower() if row[0] else ""
            name = str(row[1]).strip() if len(row) > 1 and row[1] else ""
            status = str(row[2]).strip().lower() if len(row) > 2 and row[2] else ""

            if item_type == "client" and status == "whitelist" and name:
                whitelist.append(name)

        return sorted(whitelist)

    async def get_blacklist_clients(self) -> List[str]:
        """
        Get list of clients in blacklist from "Категории" sheet.

        Returns:
            List of client names in blacklist
        """
        config = get_sheet_config("categories")

        read_start = 2
        max_row = read_start + 500
        read_range = f"B{read_start}:D{max_row}"

        try:
            data = await self.get_range(config.name, read_range)
        except HttpError:
            return []

        blacklist = []
        for row in data:
            if not row or len(row) < 3:
                continue

            item_type = str(row[0]).strip().lower() if row[0] else ""
            name = str(row[1]).strip() if len(row) > 1 and row[1] else ""
            status = str(row[2]).strip().lower() if len(row) > 2 and row[2] else ""

            if item_type == "client" and status == "blacklist" and name:
                blacklist.append(name)

        return sorted(blacklist)

    async def get_client_list_status(self, client_name: str) -> Optional[str]:
        """
        Get client's list status (whitelist/blacklist/active/None).

        Args:
            client_name: Client name to check

        Returns:
            Status string or None if not found
        """
        config = get_sheet_config("categories")

        read_start = 2
        max_row = read_start + 500
        read_range = f"B{read_start}:D{max_row}"

        try:
            data = await self.get_range(config.name, read_range)
        except HttpError:
            return None

        for row in data:
            if not row or len(row) < 3:
                continue

            item_type = str(row[0]).strip().lower() if row[0] else ""
            name = str(row[1]).strip() if len(row) > 1 and row[1] else ""
            status = str(row[2]).strip().lower() if len(row) > 2 and row[2] else ""

            if item_type == "client" and name.lower() == client_name.lower():
                return status

        return None

    async def _find_client_row_in_categories(self, client_name: str) -> Optional[int]:
        """
        Find row number for client in "Категории" sheet.

        Args:
            client_name: Client name to find

        Returns:
            Row number (1-based) or None if not found
        """
        config = get_sheet_config("categories")

        read_start = 2
        max_row = read_start + 500
        read_range = f"B{read_start}:C{max_row}"

        try:
            data = await self.get_range(config.name, read_range)
        except HttpError:
            return None

        for i, row in enumerate(data):
            if not row or len(row) < 2:
                continue

            item_type = str(row[0]).strip().lower() if row[0] else ""
            name = str(row[1]).strip() if len(row) > 1 and row[1] else ""

            if item_type == "client" and name.lower() == client_name.lower():
                return read_start + i

        return None

    async def set_client_list_status(
        self,
        client_name: str,
        status: str  # "whitelist", "blacklist", "active"
    ) -> bool:
        """
        Set client's list status in "Категории" sheet.

        If client doesn't exist in categories, adds them.

        Args:
            client_name: Client name
            status: New status ("whitelist", "blacklist", "active")

        Returns:
            True if successful
        """
        config = get_sheet_config("categories")

        # Find existing client row
        row_num = await self._find_client_row_in_categories(client_name)

        if row_num:
            # Update existing row (column D = status)
            success = await self.update_cell(config.name, row_num, "D", status)
            if success:
                logger.info(f"Updated client '{client_name}' status to '{status}'")
            return success
        else:
            # Add new client entry
            import uuid
            from datetime import datetime

            operation_id = str(uuid.uuid4())
            date_str = datetime.now().strftime("%d.%m.%Y")

            # Find first empty row
            first_empty = await self.get_first_empty_row("categories")

            # Write: A=operation_id, B=type, C=name, D=status, E=date
            row_data = [operation_id, "client", client_name, status, date_str]
            write_range = f"A{first_empty}:E{first_empty}"

            try:
                await self.update_range(config.name, write_range, [row_data])
                logger.info(f"Added client '{client_name}' with status '{status}'")
                return True
            except HttpError as e:
                logger.error(f"Error adding client to categories: {e}")
                return False

    async def add_to_whitelist(self, client_name: str) -> bool:
        """Add client to whitelist."""
        return await self.set_client_list_status(client_name, "whitelist")

    async def add_to_blacklist(self, client_name: str) -> bool:
        """Add client to blacklist."""
        return await self.set_client_list_status(client_name, "blacklist")

    async def remove_from_lists(self, client_name: str) -> bool:
        """Remove client from any list (set status to active)."""
        return await self.set_client_list_status(client_name, "active")

    async def add_category(
        self,
        category_type: str,  # "client", "designer", "expense", "income"
        name: str,
        status: str = "active"
    ) -> bool:
        """
        Add new category to "Категории" sheet.

        Args:
            category_type: Type of category (client/designer/expense/income)
            name: Name of the category
            status: Initial status (default: active)

        Returns:
            True if successful
        """
        config = get_sheet_config("categories")

        # Check if already exists
        existing = await self._find_category_row(category_type, name)
        if existing:
            logger.warning(f"Category '{name}' of type '{category_type}' already exists")
            return False

        import uuid
        from datetime import datetime

        operation_id = str(uuid.uuid4())
        date_str = datetime.now().strftime("%d.%m.%Y")

        first_empty = await self.get_first_empty_row("categories")

        # Write: A=operation_id, B=type, C=name, D=status, E=date
        row_data = [operation_id, category_type, name, status, date_str]
        write_range = f"A{first_empty}:E{first_empty}"

        try:
            await self.update_range(config.name, write_range, [row_data])
            logger.info(f"Added category: type={category_type}, name={name}")
            return True
        except HttpError as e:
            logger.error(f"Error adding category: {e}")
            return False

    async def _find_category_row(self, category_type: str, name: str) -> Optional[int]:
        """
        Find row number for category in "Категории" sheet.

        Args:
            category_type: Type of category
            name: Name to find

        Returns:
            Row number (1-based) or None if not found
        """
        config = get_sheet_config("categories")

        read_start = 2
        max_row = read_start + 500
        read_range = f"B{read_start}:C{max_row}"

        try:
            data = await self.get_range(config.name, read_range)
        except HttpError:
            return None

        for i, row in enumerate(data):
            if not row or len(row) < 2:
                continue

            item_type = str(row[0]).strip().lower() if row[0] else ""
            item_name = str(row[1]).strip() if len(row) > 1 and row[1] else ""

            if item_type == category_type.lower() and item_name.lower() == name.lower():
                return read_start + i

        return None

    async def add_new_client(self, name: str) -> bool:
        """Add new client to categories."""
        return await self.add_category("client", name, "active")

    async def add_new_designer(self, name: str) -> bool:
        """Add new designer to categories."""
        return await self.add_category("designer", name, "active")

    async def setup_categories_headers(self) -> bool:
        """
        Setup beautiful headers for "Категории" sheet.

        Creates formatted header row with proper column titles.

        Returns:
            True if successful
        """
        config = get_sheet_config("categories")

        # Beautiful headers for the categories sheet
        headers = [
            "🔑 ID операции",      # A
            "📁 Тип",              # B
            "👤 Название",         # C
            "📊 Статус",           # D
            "📅 Дата добавления",  # E
        ]

        try:
            await self.update_range(config.name, "A1:E1", [headers])
            logger.info("Categories headers set up successfully")
            return True
        except HttpError as e:
            logger.error(f"Error setting up categories headers: {e}")
            return False

    async def write_to_general(
        self,
        operation_id: str,
        date: str,
        operation_type: str,
        designer: str = "",
        client: str = "",
        order_amount: float = 0,
        designer_percent: float = 0,
        designer_salary: float = 0,
        agency_income: float = 0,
        pure_income_category: str = "",
        pure_income_amount: float = 0,
        expense_category: str = "",
        expense_amount: float = 0,
        wallet_operational: float = 0,
        wallet_reserve: float = 0
    ) -> int:
        """
        Write data directly to GENERAL sheet.

        IMPORTANT: Rows 9-12 contain FORMULAS - bot writes ONLY from row 13+

        GENERAL sheet structure:
        - A = operation_id (UUID) - HIDDEN column
        - G-U = data columns (bot writes here)

        Data columns (G-U):
        - G = дата
        - H = дизайнер
        - I = заказчик
        - J = сумма заказа
        - K = % дизайнера
        - L = ЗП дизайнера
        - M = доход агентства
        - N = категория чистого дохода
        - O = сумма чистого дохода
        - P = категория расхода
        - Q = сумма расхода
        - R = тип операции
        - S = (пусто)
        - T = операционный кошелёк
        - U = резервный кошелёк

        Args:
            operation_id: UUID of the operation
            date: Date string (DD.MM.YYYY)
            operation_type: Type of operation (designer_order, pure_order, pure_income, expense)
            designer: Designer name (for designer orders)
            client: Client name (for orders)
            order_amount: Order amount (for orders)
            designer_percent: Designer percent (for % model)
            designer_salary: Designer salary (for salary model)
            agency_income: Agency income (order_amount - designer payment)
            pure_income_category: Pure income category/name
            pure_income_amount: Pure income amount
            expense_category: Expense category
            expense_amount: Expense amount
            wallet_operational: Amount to operational wallet
            wallet_reserve: Amount to reserve wallet

        Returns:
            Row number where data was written
        """
        await self.initialize()

        # IMPORTANT: Bot writes from row 13+ only (rows 9-12 have formulas)
        START_ROW = 13

        # Find last row with data in GENERAL (column A = operation_id, starting from row 13)
        last_row = await self.get_last_data_row("GENERAL", "A", START_ROW)
        new_row = max(last_row + 1, START_ROW)

        # Prepare data for columns G-U (15 columns)
        data_columns = [
            date,                   # G: дата
            designer,               # H: дизайнер
            client,                 # I: заказчик
            order_amount or "",     # J: сумма заказа
            designer_percent or "", # K: % дизайнера
            designer_salary or "",  # L: ЗП дизайнера
            agency_income or "",    # M: доход агентства
            pure_income_category,   # N: категория чистого дохода
            pure_income_amount or "",  # O: сумма чистого дохода
            expense_category,       # P: категория расхода
            expense_amount or "",   # Q: сумма расхода
            operation_type,         # R: тип операции
            "",                     # S: (пусто)
            wallet_operational or "",  # T: операционный кошелёк
            wallet_reserve or ""    # U: резервный кошелёк
        ]

        # Write operation_id to column A (hidden)
        await self.update_cell("GENERAL", new_row, "A", operation_id)

        # Write data to columns G-U
        range_str = f"G{new_row}:U{new_row}"

        def _write():
            return self._service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'GENERAL'!{range_str}",
                valueInputOption="USER_ENTERED",
                body={"values": [data_columns]}
            ).execute()

        try:
            await self._run_sync(_write)

            # Make operation_id invisible (white text on white background)
            await self.format_cells(
                sheet_name="GENERAL",
                row_number=new_row,
                start_col="A",
                end_col="A",
                font_family="Roboto",
                font_size=8,
                font_color=(1, 1, 1)  # White - invisible
            )

            logger.info(f"Written to GENERAL row {new_row}: type={operation_type}, id={operation_id[:8]}...")
            return new_row
        except HttpError as e:
            logger.error(f"Error writing to GENERAL: {e}")
            raise

    async def delete_general_row_by_operation_id(self, operation_id: str) -> bool:
        """
        Delete a row from GENERAL sheet by operation_id.

        IMPORTANT: Searches column A starting from row 13 (rows 9-12 are formulas)

        Args:
            operation_id: UUID of the operation to delete

        Returns:
            True if deleted successfully
        """
        await self.initialize()

        # IMPORTANT: Bot data starts from row 13 (rows 9-12 have formulas)
        START_ROW = 13

        # Find row by operation_id in column A (starting from row 13)
        data = await self.get_range("GENERAL", f"A{START_ROW}:A500")
        row_to_delete = None

        for i, row in enumerate(data):
            if row and len(row) > 0 and row[0] == operation_id:
                row_to_delete = i + START_ROW  # Data starts from row 13
                break

        if row_to_delete is None:
            logger.warning(f"Operation {operation_id} not found in GENERAL")
            return False

        sheet_id = await self.get_sheet_id("GENERAL")
        if sheet_id is None:
            return False

        def _delete_row():
            request = {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": row_to_delete - 1,  # 0-based
                        "endIndex": row_to_delete
                    }
                }
            }
            return self._service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": [request]}
            ).execute()

        try:
            await self._run_sync(_delete_row)
            logger.info(f"Deleted row {row_to_delete} from GENERAL (operation_id={operation_id[:8]}...)")
            return True
        except HttpError as e:
            logger.error(f"Error deleting from GENERAL: {e}")
            return False

    async def get_analytics_data(self) -> Dict[str, Any]:
        """
        Get analytics data from GENERAL sheet.

        GENERAL sheet structure:
        - Rows 9-12: FORMULAS (reference other sheets)
        - Rows 13+: BOT DATA (direct writes)
        - Column A: operation_id (hidden)
        - Columns G-U: data

        Data columns (G-U):
        - G = дата
        - H = дизайнер
        - I = заказчик
        - J = сумма заказа
        - K = % дизайнера
        - L = ЗП дизайнера
        - M = доход агентства
        - N = категория чистого дохода
        - O = сумма чистого дохода
        - P = категория расхода
        - Q = сумма расхода
        - R = тип операции
        - S = (пусто)
        - T = операционный кошелёк
        - U = резервный кошелёк

        Summary cells:
        - G4 = Выручка (revenue)
        - I4 = Затраты (expenses)
        - K4 = Прибыль (profit)
        - M4 = Маржинальность (margin %)

        Returns:
            Dict with analytics metrics
        """
        await self.initialize()

        try:
            # Read summary cells (G4, I4, K4, M4) - they may have formulas
            summary_data = await self.get_range("GENERAL", "G4:M4")

            revenue = 0
            expenses = 0
            profit = 0
            margin = 0

            if summary_data and len(summary_data) > 0:
                row = summary_data[0]
                # G4 is index 0, I4 is index 2, K4 is index 4, M4 is index 6
                try:
                    revenue = float(row[0]) if len(row) > 0 and row[0] else 0
                except (ValueError, TypeError):
                    revenue = 0
                try:
                    expenses = float(row[2]) if len(row) > 2 and row[2] else 0
                except (ValueError, TypeError):
                    expenses = 0
                try:
                    profit = float(row[4]) if len(row) > 4 and row[4] else 0
                except (ValueError, TypeError):
                    profit = 0
                try:
                    margin = float(row[6]) if len(row) > 6 and row[6] else 0
                except (ValueError, TypeError):
                    margin = 0

            # Read data rows (G9:U500) for detailed analytics
            # New structure: G=date, H=designer, I=client, J=order_amount, K=designer%,
            #                L=designer_salary, M=agency_income, N=pure_cat, O=pure_amount,
            #                P=expense_cat, Q=expense_amount, R=type, S=empty, T=wallet1, U=wallet2
            data = await self.get_range("GENERAL", "G9:U500")

            by_designer = {}
            by_client = {}
            total_pure_income = 0
            total_expenses_detailed = 0
            total_agency_income = 0
            balance_1 = 0
            balance_2 = 0

            for row in data:
                if not row:
                    continue

                try:
                    # Index in G:U range:
                    # 0=date, 1=designer, 2=client, 3=order_amount, 4=designer%,
                    # 5=designer_salary, 6=agency_income, 7=pure_cat, 8=pure_amount,
                    # 9=expense_cat, 10=expense_amount, 11=type, 12=empty, 13=wallet1, 14=wallet2
                    designer = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                    client = str(row[2]).strip() if len(row) > 2 and row[2] else ""
                    order_amount = float(row[3]) if len(row) > 3 and row[3] else 0
                    agency_income = float(row[6]) if len(row) > 6 and row[6] else 0
                    pure_amount = float(row[8]) if len(row) > 8 and row[8] else 0
                    expense_amount = float(row[10]) if len(row) > 10 and row[10] else 0
                    b1 = float(row[13]) if len(row) > 13 and row[13] else 0
                    b2 = float(row[14]) if len(row) > 14 and row[14] else 0

                    # Track totals
                    total_pure_income += pure_amount
                    total_expenses_detailed += expense_amount
                    total_agency_income += agency_income

                    # Track wallet balances (sum all)
                    balance_1 += b1
                    balance_2 += b2

                    # Aggregate by designer
                    if designer and agency_income > 0:
                        if designer not in by_designer:
                            by_designer[designer] = 0
                        by_designer[designer] += agency_income

                    # Aggregate by client
                    if client and order_amount > 0:
                        if client not in by_client:
                            by_client[client] = 0
                        by_client[client] += order_amount

                except (ValueError, TypeError, IndexError):
                    continue

            return {
                "revenue": revenue,
                "expenses": expenses,
                "profit": profit,
                "margin": margin,
                "pure_income": total_pure_income,
                "balance_1": balance_1,  # Остаток на 1 счете
                "balance_2": balance_2,  # Остаток на 2 счете
                "by_designer": dict(sorted(by_designer.items(), key=lambda x: x[1], reverse=True)),
                "by_client": dict(sorted(by_client.items(), key=lambda x: x[1], reverse=True)),
            }

        except HttpError as e:
            logger.error(f"Error getting analytics data: {e}")
            return {
                "revenue": 0,
                "expenses": 0,
                "profit": 0,
                "margin": 0,
                "pure_income": 0,
                "balance_1": 0,
                "balance_2": 0,
                "by_designer": {},
                "by_client": {},
                "error": "Не удалось загрузить данные"
            }

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get dashboard data from GENERAL sheet.

        Reads:
        - G4 = Выручка (revenue)
        - I4 = Затраты (expenses)
        - K4 = Прибыль (profit)
        - M4 = Маржинальность (margin %)
        - T (last filled row) = На счету (account balance)

        Returns:
            Dict with dashboard metrics
        """
        await self.initialize()

        try:
            # Read summary cells (G4, I4, K4, M4)
            summary_data = await self.get_range("GENERAL", "G4:M4")

            revenue = 0
            expenses = 0
            profit = 0
            margin = 0

            if summary_data and len(summary_data) > 0:
                row = summary_data[0]
                # G4 is index 0, I4 is index 2, K4 is index 4, M4 is index 6
                revenue = float(row[0]) if len(row) > 0 and row[0] else 0
                expenses = float(row[2]) if len(row) > 2 and row[2] else 0
                profit = float(row[4]) if len(row) > 4 and row[4] else 0
                margin = float(row[6]) if len(row) > 6 and row[6] else 0

            # Read column T to find last value (account balance)
            # Data starts from row 9
            t_data = await self.get_range("GENERAL", "T9:T100")

            account_balance = 0
            if t_data:
                # Find last non-empty value
                for row in reversed(t_data):
                    if row and row[0] is not None and row[0] != "":
                        try:
                            account_balance = float(row[0])
                            break
                        except (ValueError, TypeError):
                            continue

            return {
                "revenue": revenue,
                "expenses": expenses,
                "profit": profit,
                "margin": margin,
                "account_balance": account_balance
            }

        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {
                "revenue": 0,
                "expenses": 0,
                "profit": 0,
                "margin": 0,
                "account_balance": 0,
                "error": str(e)
            }

    async def close(self) -> None:
        """Cleanup resources."""
        self._executor.shutdown(wait=False)
        logger.info("Google Sheets client closed")


# Singleton instance
_sheets_client: Optional[SheetsClient] = None


def get_sheets_client() -> SheetsClient:
    """Get or create sheets client singleton."""
    global _sheets_client
    if _sheets_client is None:
        _sheets_client = SheetsClient()
    return _sheets_client
