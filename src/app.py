import os
import boto3
import json
import requests
from datetime import datetime, timedelta, date


SLACK_WEBHOOK_URL =os.environ['SLACK_WEBHOOK_URL']


def lambda_handler(event, context) -> None:
    client = boto3.client('ce', region_name='ap-northeast-1')
    # 合計とサービス毎の請求額を取得する
    total_billing = get_total_billing(client)
    service_billings = get_service_billings(client)

    # Slack用のメッセージを作成して投げる
    (title, detail) = get_message(total_billing, service_billings)
    post_slack(title, detail)


def get_total_billing(client) -> dict:
    (start_date, end_date) = get_total_cost_date_range()

    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date,
            'End': end_date
        },
        Granularity='MONTHLY',
        Metrics=[
            'AmortizedCost'
        ]
    )
    return {
        'start': response['ResultsByTime'][0]['TimePeriod']['Start'],
        'end': response['ResultsByTime'][0]['TimePeriod']['End'],
        'billing': response['ResultsByTime'][0]['Total']['AmortizedCost']['Amount'],
    }


def get_service_billings(client) -> list:
    (start_date, end_date) = get_total_cost_date_range()

    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date,
            'End': end_date
        },
        Granularity='MONTHLY',
        Metrics=[
            'AmortizedCost'
        ],
        GroupBy=[
            {
                'Type': 'DIMENSION',
                'Key': 'SERVICE'
            }
        ]
    )
    billings = []
    for item in response['ResultsByTime'][0]['Groups']:
        billings.append({
            'service_name': item['Keys'][0],
            'billing': item['Metrics']['AmortizedCost']['Amount']
        })
    return billings


def get_message(total_billing: dict, service_billings: list) -> (str, str):
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
        'attachments': [
            {
                'color': '#36a64f',
                'pretext': title,
                'text': detail
            }
        ]
    }

    try:
        response = requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload))
    except requests.exceptions.RequestException as e:
        print(e)
    else:
        print(response.status_code)


def get_total_cost_date_range() -> (str, str):
    today = date.today()
    start_date = (today - timedelta(days=1)).isoformat()
    end_date = today.isoformat()
    return start_date, end_date
