import pymysql

def test_conn(pwd):
    try:
        conn = pymysql.connect(host='127.0.0.1', user='root', password=pwd)
        print(f'Connected with password: "{pwd}"')
        conn.cursor().execute('CREATE DATABASE IF NOT EXISTS waqt_db;')
        print('Created waqt_db')
        return True
    except Exception as e:
        print(f'Error with password "{pwd}":', e)
        return False

for p in ['', 'root', 'password']:
    if test_conn(p):
        break
