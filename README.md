使用方法：

	双击install.py安装，可自动识别操作系统

	安装后，在任意含有SQL文件的目录：shift+右键，调出CMD，输入sqla 回车！

	>cd sql_dir
	>sqla

	>sqla -f education_info_table      #寻找创建该表的文件(find)
	>sqla -d -m                        #不显示树(dry-run)，显示哪些table找不到创建，缺失(missing)
	>sqla -i a.sql                     #显示SQL文件详细：创建、依赖、缺失(info)
    >sqla -g drop-all                  #生成drop语句
	
编程方法：
	
	from sqla import SqlAnalyst
	sa=SqlAnalyst.SqlAnalyst()
	sa.run("TestDir")

run函数分析完毕后，可以用如下方法展示结果：

	sa.show()


## 简单示例：	
## 展示任务树，这里有四棵树，都依赖etl.sql
	>>> a.show()
	There are 4 trees
	Each tree's Root is marked by '*'
	* game_act_count.sql
			| etl.sql
	* cross_act_pc.sql
			| etl.sql
	* cross_diamond.sql
			| etl.sql
	* cross_act_mobile.sql
			| etl.sql
## 找出一堆SQL中的最终任务，没有其他SQL需要它们，它们应最后执行
	>>> a.show_roots()
	following SQL should be executed At Last
	[ 0 ] xinyue_tmp_deposit_numtimes_result.sql
	[ 1 ] xinyue_tmp_deposit_numtimes.sql
	[ 2 ] xinyue_tmp_deposit_habit_qq.sql
	[ 3 ] xinyue_tmp_deposit_habit_result_amount.sql
	[ 4 ] xinyue_tmp_deposit_habit_result.sql
	[ 5 ] xinyue_tmp_deposit_amount_201501.sql
	[ 6 ] toexcel.sql
	Final Tasks: 7

## 找出一堆SQL中的起始任务，要先执行这些任务
	>>> a.show_leaves()
	following SQL can be executed firstly safely
	[ 0 ] xinyue_tmp_deposit_numtimes.sql
	[ 1 ] xinyue_tmp_network.sql
	[ 2 ] xinyue_tmp_deposit_habit_qq.sql
	[ 3 ] xinyue_tmp_os.sql
	[ 4 ] xinyue_tmp_deposit_amount_201501.sql
	[ 5 ] xinyue_tmp_deposit_numtimes_result.sql
	[ 6 ] xinyue_tmp_deposit_habit_qq_amount.sql
	[ 7 ] xinyue_tmp_deposit_habit_result.sql
	Base Tasks: 8

## 展示编号为7的任务树，广度遍历。
	>>> a.show_by_root_no(7)
	* xinyue_tmp_deposit_habit_result.sql
			| xinyue_tmp_deposit_habit_qq_amount.sql

该程序随时保存着整棵树结构以及具体信息，通过该程序提供的函数，理论上您可以展示任何您可能需要的信息，包括“创建了哪些SQL、需要哪些SQL、生成了哪些内部临时VIEW”等等。

SQLA程序内含完整文档，请使用：

	sqla --help
	或
	help(sa.show)

了解高级用法