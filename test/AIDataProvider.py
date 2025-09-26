# AIDataProvider.py
from RPA.Excel.Files import Workbook

def Get_AI_Questions():
    workbook = Workbook()
    workbook.open_workbook("test/test_data1.xlsx")
    rows = workbook.read_worksheet_as_table(header=True)
    workbook.close_workbook()
    # Return list of tuples: [(question1, expected1), ...]
    return [(row["Question"], row["Expected Response"]) for row in rows]
