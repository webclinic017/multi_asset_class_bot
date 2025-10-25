from database.database_manager import DatabaseManager

db = DatabaseManager()
strategies = db.get_strategies()
hft_strategy = None
for strategy in strategies:
    if strategy['name'] == 'Market Making HFT':
        hft_strategy = strategy
        break

if hft_strategy:
    print('Strategy ID:', hft_strategy['id'])
    print('Strategy parameters:')
    for k, v in hft_strategy['parameters'].items():
        print('  {}: {}'.format(k, v))
else:
    print("Strategy not found")