#!/bin/bash

curl 'https://api-cdn.criticalmaps.net/locations' \
  --compressed \
  -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0' \
  -H 'Accept: */*' \
  -H 'Accept-Language: en-US,en;q=0.9' \
  -H 'Accept-Encoding: gzip, deflate, br, zstd' \
  -H 'Referer: https://www.criticalmaps.net/' \
  -H 'Origin: https://www.criticalmaps.net' \
  -H 'Sec-GPC: 1' \
  -H 'Connection: keep-alive' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-site' \
  -H 'Priority: u=4' \
  -H 'TE: trailers'
