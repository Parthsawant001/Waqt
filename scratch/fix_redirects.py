import re

with open('restaurants/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("return redirect('accounts:owner_register')", "return redirect('restaurants:search')")

with open('restaurants/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
