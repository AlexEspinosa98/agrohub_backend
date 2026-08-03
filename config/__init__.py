import pymysql

# Django's MySQL backend imports `MySQLdb` (mysqlclient) by default, which needs
# a compiled C extension against libmysqlclient. PyMySQL is pure Python — this
# shim makes it register as `MySQLdb` so django.db.backends.mysql keeps working
# unmodified, without requiring native build tooling in the app container.
pymysql.install_as_MySQLdb()
pymysql.version_info = (1, 4, 6, "final", 0)
