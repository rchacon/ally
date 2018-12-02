"""
Get Ally Transactions using Selenium
"""
from datetime import datetime
import json
import os
import sys

import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .dao import DAO


ALLY_URL = 'https://www.ally.com/'

SELENIUM_ADDRESS = os.environ['SELENIUM_ADDRESS']

TIMEZONE = os.environ['TIMEZONE']


def find_element_by_attribute(driver, tag_name, attribute, value):
    elements = driver.find_elements_by_tag_name(tag_name)
    for element in elements:
        val = element.get_attribute(attribute)
        if val == value:
            return element


class AllyScraperException(Exception):
    pass


class AllyScraper:

    def __init__(self, username, password, account):
        self.username = username
        self.password = password
        self.account = account

        self.driver = webdriver.Remote(
            command_executor=SELENIUM_ADDRESS,
            desired_capabilities=DesiredCapabilities.CHROME
        )
        self.driver.implicitly_wait(10)  # seconds

    def login(self):
        # Click login
        self.driver.get(ALLY_URL)
        self.driver.find_element_by_id('login-btn').click()

        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, 'login-widget'))
        )

        # Select account type
        self.driver.find_element_by_xpath("//select[@id='account']/option[text()='Bank or Invest Login']").click()

        username_el = self.driver.find_element_by_id('username')
        username_el.send_keys(self.username)

        password_el = self.driver.find_element_by_id('password')
        password_el.send_keys(self.password)

        submit_el = find_element_by_attribute(self.driver, 'button', 'data-id', 'submit')
        submit_el.click()

    def goto_account_page(self):
        acct_containers = self.driver.find_elements_by_class_name('accounts-individual-container')

        for container in acct_containers:
            spans = container.find_elements_by_tag_name('span')
            for span in spans:
                if '...%s' % self.account in span.text:
                    link = WebDriverWait(container, 10).until(
                        EC.element_to_be_clickable((By.TAG_NAME, 'a'))
                    )
                    link.click()
                    return

        raise Exception('Account %s not found', self.account)

    def get_transactions(self, since=None):
        transactions = []

        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, 'transactions-history-table'))
        )
        transaction_tables = self.driver.find_elements_by_class_name('transactions-history-table')
        for table in transaction_tables[1:]:  # skip first table which is empty
            # Expand section of transactions
            try:
                caption = table.find_element_by_xpath(".//caption[contains(@class, 'transaction-collapsible-header')]")
            except:
                pass
            else:
                caption.click()

            rows = table.find_elements_by_tag_name('tr')[1:]  # skip header row

            for row in rows:
                cols = row.find_elements_by_tag_name('td')
                if len(cols) != 4:
                    continue

                if cols[1].get_attribute('class') != 'description':
                    continue

                # Skip pending transactions
                if cols[0].text == 'Pending':
                    continue

                description_link = cols[1]
                description_link.click()

                # Get ul from next collapsed row which contains time and transaction type
                wait = WebDriverWait(self.driver, 10)
                ul = wait.until(
                    EC.visibility_of_element_located((By.XPATH, './/tr/td[2]/div/ul'))
                )

                trans_time = ul.find_element_by_xpath('.//li[3]/span').text
                trans_type = ul.find_element_by_xpath('.//li[4]/span').text

                posted_at = datetime.strptime(cols[0].text + ' ' + trans_time, '%b %d, %Y %H:%M %p')
                posted_at_local = pytz.timezone(TIMEZONE).localize(posted_at)
                posted_at_utc = posted_at_local.astimezone(pytz.utc)

                transaction = {'posted_at': posted_at_utc,
                               'type': trans_type,
                               'description': description_link.text.strip(),
                               'amount': cols[2].text,
                               'balance': cols[3].text}

                # done processing new transactions
                if transaction == since:
                    print('Already processed: %s' % since)
                    return transactions

                transactions.append(transaction)

        return transactions

    def run(self, since=None):
        transactions = []

        try:
            self.login()
            self.goto_account_page()
            transactions = self.get_transactions(since=since)
        except Exception as e:
            raise AllyScraperException from e
        finally:
            self.driver.close()

        return transactions


def main(args, password):
    params = {}

    if args.save:
        dao = DAO()
        params['since'] = dao.get_last_transaction()

    ally = AllyScraper(args.username, password, args.account)
    transactions = ally.run(**params)

    if not transactions:
        sys.exit('No transactions found')

    if args.save:
        for transaction in reversed(transactions):  # Insert older transactions first
            dao.save_transaction(transaction)

        dao.close()
    else:
        def json_encoder(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError('Type %s not serializable' % type(obj))

        print(json.dumps(transactions, indent=2, default=json_encoder))


if __name__ == '__main__':
    import argparse
    import getpass

    parser = argparse.ArgumentParser()

    parser.add_argument('username', help='Bank username')
    parser.add_argument('account', help='Last four digits of account')
    parser.add_argument('--save', help='Save to Postgres', action='store_true')
    args = parser.parse_args()

    password = getpass.getpass('Password: ')

    main(args, password)
