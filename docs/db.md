# 数据库部分的文档

## sqlite3 库的使用

> 请以[官方文档](https://docs.python.org/zh-cn/3.12/library/sqlite3.html)为准噢w

数据库操作的基本流程大概是：

连接到数据库 `conn = sqlite3.connect("example.db")`
->
创建游标 `cur = conn.cursor()`
->
执行语句 `cur.execute(...)`
->
获取结果/提交事务 `result = cur.fetchall()` / `conn.commit()`
->
关闭游标 `cur.close()`
->
关闭连接 `conn.close()`

将上述过程封装成类或许更方便操作。

### Connection

被称作「连接」，由 `sqlite3.connect(database, ...)` 函数返回，是 `sqlite3` 操作数据库的前提。相当于 `requests` 中的 `Session` 对象，表示一次和数据库的会话。调用 `close()` 来关闭连接，支持通过 `with` 进行自动上下文管理。

文件路径除了填本地文件路径外，也可以填 `":memory:"` 来打开一个仅存在于内存中的 sqlite 数据库。

连接不一定线程安全的，需要根据 `sqlite3.threadsafety` 的值确定（经测试一般为`3`，表示线程安全）[^1]。不过除此之外从性能角度考量，一般也会为每个线程都临时创建一个连接，操作完成后关闭。

[^1]: <https://docs.python.org/zh-cn/3.12/library/sqlite3.html#sqlite3.threadsafety>

如果对数据库有修改，默认需要手动调用 `commit()` 方法来提交。如果使用 `with` 自动管理上下文，块结束时也会自动提交。

### Cursor

被称作「游标」，由 `Connection.cursor()` 方法返回，是 `sqlite3` 操作数据库的核心接口。不支持通过 `with` 进行自动上下文管理，但 `close()` 方法会在被删除时被自动调用（也可以手动提前调用）

得到游标之后就可以对数据库做操作了。

以下是部分方法：[^2]

[^2]: <https://docs.python.org/zh-cn/3.12/library/sqlite3.html#sqlite3.Cursor>

#### execute(sql, parameters=())

执行*一条* SQL 语句，同时提供数据绑定方法以防止注入。不过如果要编写的部分不是用户能接触到的，用字符串格式化或拼接也没问题，但还是请务必小心。

> 要执行多条，使用 `executemany(...)`

提供的数据绑定方法与字符串格式化的形式很像，在 SQL 语句中使用占位符，`parameters` 中的对应参数会被自动绑定到对应位置。可以使用问号占位和命名占位两种风格，分别类似于格式化字符串中的位置格式化和关键字格式化。

##### 问号占位

在语句中使用 `?` 占位

此时 `parameters` 必须是一个长度与占位符的数量相匹配的 `Sequence`

##### 命名占位

在语句中使用 `:key` 占位

此时 `parameters` 必须是 `dict`（或其子类）的实例，它必须包含与所有命名参数相对应的键（额外的将被忽略）

> sqlite3 防止 SQL 注入的方法不是简单的转义。它会先对语句进行预编译，再将提供的参数绑定到语句中。此时提供的参数仅会被视为纯粹的值，不可能与语句混淆。

#### fetchall()

在执行了一个查询语句之后，可使用 `fetchall()` 方法获得所有的查询结果。

> 也可使用 `fetchone()` `fetchmany()` 获得一个、多个查询结果。

也可以使用 `for` 语句遍历游标对象作为替代。

## SQL 语句的使用

*部分特性是 SQLite 特有的，可能无法在别的数据库中使用*

### `CREATE TABLE`

用于创建一个新表。

**语法**：

```sql
CREATE TABLE table_name
(
    column_name1 data_type,
    column_name2 data_type,
    column_name3 data_type,
    ...
);
```

- `table_name`：新表的名称。
- 列定义以括号括起，并用逗号分隔。每个列定义包括列名称 (`column_name`) 和数据类型 (`data_type`)。

**额外语法**：

- `AUTOINCREMENT`：用于使某列在插入数据时自动递增，通常用于整型字段。使用该修饰符后，插入操作无需显式指定该列的值。
- `PRIMARY KEY`：用于定义表的主键，确保每条记录的唯一性。`PRIMARY KEY` 通常与 `AUTOINCREMENT` 配合使用。
- `NOT NULL`：用于限制某列不能为空值。如果列未标记为 `NOT NULL`，则在插入数据时可以留空。

### `INSERT INTO`

用于向表中插入新记录。

**语法**：

```sql
INSERT INTO table_name (column1, column2, column3, ...)
VALUES (value1, value2, value3, ...);
```

- `table_name`：目标表的名称。
- 列名称列表用括号括起，并用逗号分隔。可省略此列表，若省略则采用表定义时的列顺序。
- `VALUES`：紧随其后的括号中包含与列对应的数据值，按列名称的顺序进行匹配。

### `SELECT`

用于查询表中的数据。

**语法**：

```sql
SELECT column1, column2, column3, ...
FROM table_name
WHERE condition;
```

- `table_name`：目标表的名称。
- 在 `SELECT` 关键字后列出要查询的列名称，以逗号分隔。使用 `*` 可选择查询所有列。
- `WHERE` 子句用于指定查询条件（可选）。

### `UPDATE`

用于更新表中现有记录的内容。

**语法**：

```sql
UPDATE table_name
SET column1 = value1, column2 = value2, ...
WHERE condition;
```

- `table_name`：目标表的名称。
- `SET` 子句后列出要更新的列及其对应的新值，以逗号分隔。
- `WHERE` 子句用于限制要更新的行（可选）。如果未指定 `WHERE` 子句，将更新表中的所有行。

### `DELETE`

用于删除表中的指定记录。

**语法**：

```sql
DELETE FROM table_name
WHERE condition;
```

- `table_name`：目标表的名称。
- `WHERE` 子句用于指定要删除的记录。如果未指定 `WHERE` 子句，将删除表中的所有记录。

### `VACUUM`

用于清理数据库文件。

**语法**：

```sql
VACUUM;
```

- 此命令回收未使用的空间，优化数据库文件的大小和性能。
