with open('app/payments/views.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
with open('app/payments/views.py', 'w', encoding='utf-8') as f:
    f.writelines([line[1:] if line.startswith(' ') else line for line in lines])
