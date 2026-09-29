SELECT table_name, GROUP_CONCAT(column_name ORDER BY seq_in_index) pk
FROM information_schema.statistics WHERE table_schema=DATABASE() AND index_name='PRIMARY'
GROUP BY table_name ORDER BY table_name;
