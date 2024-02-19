def create_notify_function(
    channel_name: str,
    function_name: str,
) -> str:
    return f"""
CREATE OR REPLACE FUNCTION {function_name}_{channel_name}() RETURNS TRIGGER AS $$
  BEGIN
    PERFORM pg_notify(
      '{channel_name}',
      json_build_object(
        'operation', lower(TG_OP),
        'table', TG_TABLE_NAME,
        'sent_at', NOW()
      )::text);
    RETURN NEW;
  END;
  $$ LANGUAGE plpgsql;
"""


def create_after_change_trigger(
    table_name: str,
    channel_name: str,
    function_name: str,
    trigger_name_prefix: str,
) -> str:
    return f"""
CREATE OR REPLACE TRIGGER {trigger_name_prefix}{table_name}
  AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON {table_name}
  EXECUTE FUNCTION {function_name}_{channel_name}();
"""


def fetch_trigger_names(prefix: str) -> str:
    return f"""
SELECT
  event_object_table AS table,
  trigger_name
FROM
  information_schema.triggers
WHERE
  trigger_name LIKE '{prefix}%'
"""


def drop_trigger(trigger_name: str, table: str) -> str:
    return f"""DROP TRIGGER IF EXISTS {trigger_name} ON {table};"""


def drop_function(name: str) -> str:
    return f"""DROP FUNCTION IF EXISTS {name}();"""
