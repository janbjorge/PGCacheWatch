def notify_function(
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


def after_change_trigger(
    table_name: str,
    channel_name: str,
    function_name: str,
    trigger_name_prefix: str,
) -> str:
    return f"""
CREATE OR REPLACE TRIGGER {trigger_name_prefix}{table_name}
  AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON {table_name}
  FOR EACH ROW EXECUTE PROCEDURE {function_name}_{channel_name}();
"""
