-- 仅在空数据目录首次初始化时由 docker-entrypoint 执行。
-- 已有卷请依赖 scripts/ensure-shared-databases.sh。
SELECT 'CREATE DATABASE gweb_db OWNER geo_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'gweb_db')\gexec
