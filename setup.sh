virtualenv -p 3.9 .virtualenv
source ./.virtualenv/bin/activate
pip install -r ./order_reformer_function/requirements.txt
cp ./.env.template ./.env