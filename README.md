# ally

Get my Ally transactions as far back as possible

## Usage

Copy environment file and update values. `timezone` should be set to your local timezone to assist with converting localized timestamps from ally.com to UTC.

```
cp example.env .env
```

Run selenium locally rather than in a container. When logging in for the first time you will need to complete a two-step verification process which will be difficult with a headless browser.

Run postgres
```
docker-compose up -d ally-db
```

Run scraper
```
docker-compose run --rm ally-scraper
```
