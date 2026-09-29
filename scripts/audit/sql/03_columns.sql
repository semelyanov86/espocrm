-- Physical columns of the source schema.
SELECT table_name, column_name, ordinal_position, data_type, column_type, is_nullable, column_key
FROM information_schema.columns WHERE table_schema=DATABASE() ORDER BY table_name, ordinal_position;
