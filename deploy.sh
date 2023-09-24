if [ $# -lt 2 ]; then
        echo "need EnvironmentName[dev|stg|prd] WebHookURL"
        exit 1
    fi

echo "deploy to pipeline"

sam build

sam deploy --template-file template.yaml  \
    --stack-name $1-developer-tools-alert-cost \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides SlackWebhookUrl=$2
