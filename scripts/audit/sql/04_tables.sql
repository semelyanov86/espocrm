-- Tables with engine/size estimates (exact counts are generated separately).
SELECT table_name, engine, table_rows approx_rows, data_length+index_length bytes, IFNULL(auto_increment,'') auto_inc, create_time, IFNULL(update_time,'') update_time
FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE' ORDER BY table_name;
