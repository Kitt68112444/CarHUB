import easyocr
reader = easyocr.Reader(['th','en'])
result = reader.readtext("pay_slip.jpg")
for r in result:
    print(r[1])
