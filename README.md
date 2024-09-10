# Typo Master


# 安装依赖

https://github.com/shibing624/pycorrector/tree/master/pycorrector
模型文件下载，参考：
```text
https://github.com/shibing624/pycorrector/issues/119
```
下载好之后放在`~/.pycorrector/datasets`文件夹下.




语言：Python
输入：Git仓库
扫描内容：
- Markdown（v0.0.1）
- 代码文件
  - 注释
  - 函数名 
  - 





# 一、目标

## 第一阶段目标  

用于从GitHub上寻找有拼写错误的并且有一些Star的项目来用于蹭PR。

## 第二阶段目标

寻找高赞但是没有中文使用文档的项目 

## 第三阶段目标

用于从GitHub上寻找有待解决的Bug或者Feature的项目。 

## 第四阶段目标

对GitHub上的项目自动审计、Review，检出Bug或者漏洞进行修复。



此项目只负责完成第一阶段的目标，如果能成功完成，会有后续项目继续接力完成后续目标。



# 第一阶段的实现思路

## 项目的获取 

- 按照人的粉丝之类的去搜索寻找
- 按照标签搜索寻找

## 项目的检查

- 中文词典
- 英文词典 
- 对于有过合并typo先例的项目增加其权重推荐优先撸它
  - 判断依据是pr合并，并且commit中有typo关键字 









