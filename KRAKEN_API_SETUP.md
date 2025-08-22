# Kraken API Setup Guide

## 🔑 **Where to Add Your Kraken API Credentials**

### **Step 1: Locate the Configuration File**
Your Kraken API credentials go in the main configuration file:
```
multi_asset_bot/config/config.yaml
```

### **Step 2: Find the Kraken Section**
Look for lines **19-21** in the config file:

```yaml
  kraken:
    api_key: ""  # Add your Kraken API key
    api_secret: ""  # Add your Kraken API secret
```

### **Step 3: Add Your Credentials**
Replace the empty strings with your actual Kraken API credentials:

```yaml
  kraken:
    api_key: "your_actual_kraken_api_key_here"
    api_secret: "your_actual_kraken_api_secret_here"
```

**Example:**
```yaml
  kraken:
    api_key: "abcd1234efgh5678ijkl9012mnop3456"
    api_secret: "xyz789abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567=="
```

---

## 🏗️ **How to Get Kraken API Credentials**

### **Step 1: Create a Kraken Account**
1. Go to [kraken.com](https://www.kraken.com)
2. Sign up for an account
3. Complete the verification process

### **Step 2: Generate API Keys**
1. **Log in** to your Kraken account
2. Go to **Settings** → **API**
3. Click **"Generate New Key"**
4. **Configure Permissions:**
   - ✅ **Query Funds** (required for balance checking)
   - ✅ **Query Open Orders** (required for order management)
   - ✅ **Query Closed Orders** (required for trade history)
   - ✅ **Query Ledger Entries** (optional, for detailed history)
   - ✅ **Create & Modify Orders** (required for live trading)
   - ✅ **Cancel Orders** (required for order management)
   - ❌ **Withdraw Funds** (NOT recommended for security)

### **Step 3: Copy Your Credentials**
1. **API Key**: Copy the public key (starts with letters/numbers)
2. **API Secret**: Copy the private key (longer, includes special characters)
3. **Store Securely**: Save these in a secure location

---

## 🔒 **Security Best Practices**

### **API Key Security**
- ✅ **Never share** your API credentials
- ✅ **Use IP restrictions** if possible (limit to your trading server IP)
- ✅ **Disable withdrawal permissions** for trading bots
- ✅ **Use separate keys** for different applications
- ✅ **Regularly rotate** your API keys

### **Configuration File Security**
- ✅ **Never commit** config files with real credentials to version control
- ✅ **Use environment variables** for production deployments
- ✅ **Set proper file permissions** (readable only by your user)

### **Alternative: Environment Variables (Recommended for Production)**
Instead of putting credentials directly in the config file, you can use environment variables:

1. **Set environment variables:**
```bash
export KRAKEN_API_KEY="your_api_key_here"
export KRAKEN_API_SECRET="your_api_secret_here"
```

2. **Update config.yaml:**
```yaml
  kraken:
    api_key: ${KRAKEN_API_KEY}
    api_secret: ${KRAKEN_API_SECRET}
```

---

## 🧪 **Testing Your Setup**

### **Test 1: Basic Connection**
Run this command to test your Kraken connection:
```bash
cd multi_asset_bot
python -c "
from data.kraken_feed import KrakenDataFeed
import yaml

with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

kraken = KrakenDataFeed(config)
price = kraken.get_current_price('SOLUSD')
print(f'Current SOL/USD price: ${price}')
"
```

### **Test 2: Account Balance (Requires API Credentials)**
```bash
cd multi_asset_bot
python -c "
from data.kraken_feed import KrakenDataFeed
import yaml

with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

kraken = KrakenDataFeed(config)
balance = kraken.get_account_balance()
if balance:
    print('Account balance retrieved successfully!')
    for asset, amount in balance.items():
        if float(amount) > 0:
            print(f'{asset}: {amount}')
else:
    print('Failed to retrieve balance - check your API credentials')
"
```

### **Test 3: Full Multi-Asset Backtest**
```bash
cd multi_asset_bot
python main.py --mode backtest
```

---

## 🚨 **Troubleshooting**

### **Common Issues**

#### **"API credentials not provided"**
- **Solution**: Make sure you've added your API key and secret to the config file
- **Check**: Lines 20-21 in `config/config.yaml` should have your actual credentials

#### **"Kraken API error: Invalid key"**
- **Solution**: Double-check that you copied the API key correctly
- **Check**: Make sure there are no extra spaces or characters

#### **"Kraken API error: Invalid signature"**
- **Solution**: Double-check that you copied the API secret correctly
- **Check**: The API secret should be the longer string with special characters

#### **"Permission denied"**
- **Solution**: Make sure your API key has the required permissions
- **Check**: Go back to Kraken settings and verify permissions are enabled

#### **"No data retrieved for SOL/USD"**
- **Solution**: This is normal for backtesting (uses demo data)
- **Check**: For live trading, make sure you have SOL in your account

---

## 📋 **Quick Setup Checklist**

- [ ] Created Kraken account and completed verification
- [ ] Generated API key with proper permissions
- [ ] Added API credentials to `config/config.yaml` (lines 20-21)
- [ ] Tested connection with current price check
- [ ] Tested account balance retrieval (if using live credentials)
- [ ] Ran successful multi-asset backtest
- [ ] Secured API credentials properly

---

## 🎯 **Ready to Trade**

Once you've completed the setup:

1. **Backtesting**: Works without API credentials (uses demo data)
2. **Live Trading**: Requires valid API credentials with trading permissions
3. **Paper Trading**: Test with small amounts first

**Example Commands:**
```bash
# Backtest (no credentials needed)
python main.py --mode backtest

# Live trading (requires credentials)
python main.py --mode live

# Optimization (no credentials needed for backtesting)
python main.py --mode optimize
```

---

**🔐 Remember: Keep your API credentials secure and never share them publicly!**