#!/bin/sh

set -eu

usage() {
  printf 'Usage: %s N [OUTPUT_FILE]\n' "$(basename "$0")" >&2
  printf 'Example: %s 100 ./maccy-last-100.txt\n' "$(basename "$0")" >&2
}

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  usage
  exit 2
fi

entry_count=$1
output_file=${2:-./maccy-history.txt}

case $entry_count in
  ''|*[!0-9]*|0)
    printf 'Error: N must be a positive integer.\n' >&2
    exit 2
    ;;
esac

if ! command -v sqlite3 >/dev/null 2>&1; then
  printf 'Error: sqlite3 was not found. It is normally included with macOS.\n' >&2
  exit 1
fi

maccy_db=${MACCY_DB_PATH:-}
if [ -z "$maccy_db" ]; then
  for candidate in \
    "$HOME/Library/Containers/org.p0deje.Maccy/Data/Library/Application Support/Maccy/Storage.sqlite" \
    "$HOME/Library/Application Support/Maccy/Storage.sqlite"
  do
    if [ -f "$candidate" ]; then
      maccy_db=$candidate
      break
    fi
  done
fi

if [ -z "$maccy_db" ] || [ ! -f "$maccy_db" ]; then
  printf 'Error: could not find the Maccy database.\n' >&2
  printf 'Looked in Maccy’s sandbox and standard Application Support folders.\n' >&2
  exit 1
fi

case $output_file in
  /*) ;;
  *) output_file=$PWD/$output_file ;;
esac

output_dir=$(dirname "$output_file")
if [ ! -d "$output_dir" ]; then
  printf 'Error: output directory does not exist: %s\n' "$output_dir" >&2
  exit 1
fi

temporary_file=$(mktemp "$output_dir/.maccy-history.XXXXXX")
cleanup() {
  if [ -n "${temporary_file:-}" ]; then
    rm -f "$temporary_file"
  fi
}
trap cleanup EXIT HUP INT TERM

# Each HistoryItem may contain several pasteboard representations (plain text,
# HTML, RTF, image data, and so on). Select one preferred plain-text value per
# item and reject entries that also contain file or image data.
#
# Embedded CR/LF characters are emitted unchanged, so a multiline clipboard
# item remains multiline in the output. SQLite adds one newline after each
# clipboard item to separate it from the next item.
if ! sqlite3 -readonly "$maccy_db" "
WITH recent_items AS (
  SELECT
    item.Z_PK AS item_id,
    item.ZLASTCOPIEDAT AS copied_at,
    CAST(content.ZVALUE AS TEXT) AS text_value
  FROM ZHISTORYITEM AS item
  JOIN ZHISTORYITEMCONTENT AS content
    ON content.ZITEM = item.Z_PK
  WHERE content.ZTYPE IN ('public.utf8-plain-text', 'public.text')
    AND content.ZVALUE IS NOT NULL
    AND content.Z_PK = (
      SELECT preferred.Z_PK
      FROM ZHISTORYITEMCONTENT AS preferred
      WHERE preferred.ZITEM = item.Z_PK
        AND preferred.ZTYPE IN ('public.utf8-plain-text', 'public.text')
        AND preferred.ZVALUE IS NOT NULL
      ORDER BY CASE preferred.ZTYPE
                 WHEN 'public.utf8-plain-text' THEN 0
                 ELSE 1
               END,
               preferred.Z_PK
      LIMIT 1
    )
    AND NOT EXISTS (
      SELECT 1
      FROM ZHISTORYITEMCONTENT AS nontext
      WHERE nontext.ZITEM = item.Z_PK
        AND nontext.ZTYPE IN (
          'public.file-url',
          'public.png',
          'public.tiff',
          'public.jpeg',
          'public.heic'
        )
    )
  ORDER BY item.ZLASTCOPIEDAT DESC, item.Z_PK DESC
  LIMIT $entry_count
)
SELECT text_value
FROM recent_items
ORDER BY copied_at ASC, item_id ASC;
" > "$temporary_file"
then
  printf 'Error: Maccy’s database could not be queried. Its internal schema may have changed.\n' >&2
  exit 1
fi

mv -f "$temporary_file" "$output_file"
temporary_file=''

printf 'Wrote the latest text entries, oldest to newest, to %s\n' "$output_file"
