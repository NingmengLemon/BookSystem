# 大概是一些想法

## 任务4

### 数据模型

#### 用户模型

- id: str (UUID4)
- username: str
- nickname: str
- gender: int (enum)
- salt: str
- password: str (sha256 salted)

#### 书籍模型

- id: str (UUID4)
- name: str
- isbn: str
- author: str
- publisher: str
- desc: str
- cover: str (uri)
- extra: str (JSON or empty)
- belongto: str (UUID4 of user)

### API

#### 登录

- 获取某个用户名对应的盐值
- 登录验证
- 退出登录
- 获取登录信息

#### 书籍操作

- 查询
- 增加
- 修改
- 删除
