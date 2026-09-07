# 数据字典格式示例

> 本文件展示数据字典的标准格式，用于从 Excel/Word 解析后生成数据字段章节。

---

## 格式说明

数据字典以表格形式呈现，每行定义一个字段。解析时识别以下列：

| 列名（可选别名） | 必需 | 说明 |
|------------------|------|------|
| 字段名 / field_name / column | 是 | 字段的英文标识 |
| 类型 / type / data_type | 是 | 数据类型（见下方类型映射） |
| 必填 / required / nullable | 否 | 是否必填，默认"否" |
| 说明 / description / comment | 否 | 字段的业务含义 |
| 默认值 / default | 否 | 默认值 |
| 长度 / length / max_length | 否 | 字符串/数值的最大长度 |
| 约束 / constraint | 否 | 唯一、外键等约束 |

---

## 数据类型映射

| 原始类型 | 标准化类型 | 说明 |
|----------|------------|------|
| string, varchar, text, char, nvarchar | string | 文本类型 |
| int, integer, bigint, smallint, tinyint | integer | 整数 |
| decimal, float, double, numeric, money | number | 浮点数 |
| datetime, timestamp, date, time | datetime | 日期时间 |
| boolean, bit, bool | boolean | 布尔值 |
| json, jsonb, xml | object | 结构化数据 |
| uuid, guid | string (uuid) | UUID 格式 |

---

## 示例：用户表

| 字段名 | 类型 | 必填 | 说明 | 默认值 |
|--------|------|------|------|--------|
| id | string (uuid) | 是 | 用户唯一标识 | 系统生成 |
| username | string | 是 | 用户名，3-20位字母数字 | - |
| email | string | 是 | 邮箱地址，唯一 | - |
| phone | string | 否 | 手机号码 | null |
| password_hash | string | 是 | 密码哈希值 | - |
| role | string | 是 | 用户角色：admin/member | member |
| status | string | 是 | 状态：active/inactive/banned | active |
| created_at | datetime | 是 | 注册时间 | 系统当前时间 |
| updated_at | datetime | 是 | 最后更新时间 | 系统当前时间 |

---

## 示例：订单表

| 字段名 | 类型 | 必填 | 说明 | 默认值 |
|--------|------|------|------|--------|
| id | string (uuid) | 是 | 订单唯一标识 | 系统生成 |
| user_id | string (uuid) | 是 | 关联用户ID | - |
| order_no | string | 是 | 订单编号，格式: ORD+年月日+序号 | 系统生成 |
| total_amount | number | 是 | 订单总金额 | 0.00 |
| status | string | 是 | 状态：pending/paid/shipped/completed/cancelled | pending |
| payment_method | string | 否 | 支付方式：wechat/alipay/bank | null |
| shipping_address | string | 否 | 收货地址 | null |
| created_at | datetime | 是 | 下单时间 | 系统当前时间 |
| paid_at | datetime | 否 | 支付时间 | null |
| shipped_at | datetime | 否 | 发货时间 | null |
