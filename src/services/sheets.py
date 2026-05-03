import json
import logging
import os

import gspread

logger = logging.getLogger(__name__)


def _get_spreadsheet():
    creds = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    gc = gspread.service_account_from_dict(creds)
    spreadsheet_id = os.environ["GOOGLE_SPREADSHEET_ID"]
    return gc.open_by_key(spreadsheet_id)


def append_to_revenue(event_date, floor, quantity: int, amount_som: float) -> bool:
    try:
        sh = _get_spreadsheet()
        ws = sh.worksheet("Выручка")
        ws.append_row([
            str(event_date),
            floor if floor is not None else "—",
            quantity,
            amount_som,
        ])
        return True
    except Exception as e:
        logger.error(f"Sheets append_to_revenue failed: {e}")
        return False


def append_to_expenses(event_date, event_type: str, description: str,
                       amount_som: float) -> bool:
    try:
        sh = _get_spreadsheet()
        ws = sh.worksheet("Расходы")
        ws.append_row([str(event_date), event_type, description or "", amount_som])
        return True
    except Exception as e:
        logger.error(f"Sheets append_to_expenses failed: {e}")
        return False


def append_to_profit(event_date, revenue: float, expenses: float,
                     profit: float) -> bool:
    try:
        sh = _get_spreadsheet()
        ws = sh.worksheet("Прибыль")
        ws.append_row([str(event_date), revenue, expenses, profit])
        return True
    except Exception as e:
        logger.error(f"Sheets append_to_profit failed: {e}")
        return False
