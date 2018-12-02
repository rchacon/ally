import os

import psycopg2.extras


class DAO:

    def __init__(self):
        self._cursor = None

    @property
    def cursor(self):
        if self._cursor is not None:
            return self._cursor

        conn = psycopg2.connect(host=os.environ['POSTGRES_HOST'],
                                port=os.environ['POSTGRES_PORT'],
                                dbname=os.environ['POSTGRES_DB'],
                                user=os.environ['POSTGRES_USER'],
                                password=os.environ['POSTGRES_PASSWORD'])
        conn.autocommit = True
        self._cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        return self._cursor

    def close(self):
        if self._cursor:
            self._cursor.connection.close()
            self._cursor.close()

    def save_transaction(self, transaction):
        stmt = """
            INSERT INTO ally_transactions
            (posted_at, type, description, amount, balance) VALUES
            (%(posted_at)s, %(type)s, %(description)s, %(amount)s, %(balance)s)
            RETURNING id
        """
        self.cursor.execute(stmt, transaction)

        return self.cursor.fetchone()[0]

    def get_last_transaction(self):
        stmt = """
            SELECT posted_at, type, description, amount, balance
            FROM ally_transactions order by posted_at desc limit 1
        """
        self.cursor.execute(stmt)

        row = self.cursor.fetchone()

        if row:
            row = dict(row)

        return row
