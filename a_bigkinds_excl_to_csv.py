import csv
from openpyxl import load_workbook

load_wb = load_workbook("NewsResult_20210203-20220203.xlsx", data_only=True)
load_ws = load_wb['sheet']

data_list = []

include_list = [1, 2, 4]

for row in load_ws.rows:
    cell_list = []
    for i, cell in enumerate(row):
        if i in include_list:
            cell_list.append(cell.value)
    data_list.append(cell_list)



with open("./NewsResult.csv", 'w', newline='') as f:
    w = csv.writer(f)

    for value in data_list:
        w.writerow(value)





