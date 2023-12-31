from datetime import datetime, timedelta, date
import json
import os
import requests
from typing import Union

import boto3


SLACK_WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']


def get_total_billing(client: object) -> dict:
    start_date, end_date = get_total_cost_date_range()

    res = client.get_cost_and_usage(
        TimePeriod={'Start': start_date, 'End': end_date},
        Granularity='MONTHLY',
        Metrics=['AmortizedCost']
    )
    return {
        'start': res['ResultsByTime'][0]['TimePeriod']['Start'],
        'end': res['ResultsByTime'][0]['TimePeriod']['End'],
        'billing': res['ResultsByTime'][0]['Total']['AmortizedCost']['Amount'],
    }


def get_service_billings(client: object) -> list:
    start_date, end_date = get_total_cost_date_range()

    response = client.get_cost_and_usage(
        TimePeriod={'Start': start_date,'End': end_date},
        Granularity='MONTHLY',
        Metrics=['AmortizedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
    )
    return [
        {'service_name': item['Keys'][0],
        'billing': item['Metrics']['AmortizedCost']['Amount']
        } for item in response['ResultsByTime'][0]['Groups']
    ]


def get_message(total_billing: dict, service_billings: list) -> Union[str, str]:
    start = datetime.strptime(total_billing['start'], '%Y-%m-%d').strftime('%m/%d')
    total = round(float(total_billing['billing']), 2)
    title = f'{start}の請求額は、{total:.2f} USDです。'

    data = {}
    for item in service_billings:
        billing = round(float(item['billing']), 2)
        if billing == 0.0:
            continue
        data[item['service_name']] = billing

    details = []
    for k, v in sorted(data.items(), key=lambda x: x[1], reverse=True):
        details.append(f'　・{k}: {v:.2f} USD')
    return title, '\n'.join(details)


def post_slack(title: str, detail: str) -> None:
    payload = {
        'attachments': [{'color': '#36a64f', 'pretext': title, 'text': detail}]
    }

    try:
        response = requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload))
    except requests.exceptions.RequestException as e:
        print(e)
    else:
        print(response.status_code)


def get_total_cost_date_range() -> Union[str, str]:
    today = date.today()
    start_date = (today - timedelta(days=1)).isoformat()
    end_date = today.isoformat()
    return start_date, end_date


def lambda_handler(event, context) -> None:
    client = boto3.client('ce', region_name='ap-northeast-1')
    # 合計とサービス毎の請求額を取得する
    total_billing = get_total_billing(client)
    service_billings = get_service_billings(client)
    # Slack用のメッセージを作成して投げる
    title, detail = get_message(total_billing, service_billings)
    post_slack(title, detail)
