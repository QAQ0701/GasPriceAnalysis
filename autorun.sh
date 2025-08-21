#!/bin/bash

#chmod +x /Users/o_o/Documents/GitHub/GasPriceAnalysis/scrape_gasprice.py /Users/o_o/Documents/GitHub/GasPriceAnalysis/clean_data.py /Users/o_o/Documents/GitHub/GasPriceAnalysis/visualization.py
#chmod +x /Users/o_o/Documents/GitHub/GasPriceAnalysis/autorun.sh
#grep CRON /var/log/system.log

# Run the first Python script
cd /Users/o_o/Documents/GitHub/GasPriceAnalysis

echo "Running scrape_gasprice.py..."
python3 ./scrape_gasprice.py

# Check if the first script ran successfully
if [ $? -ne 0 ]; then
    echo "scrape_gasprice.py failed with error:"
    echo "$error_message"
    exit 1
    # echo "scrape_gasprice.py failed. Retrying in 1 minute..."
    # sleep 60  # Wait for 1 minute
    # python3 ./scrape_gasprice.py
    # if [ $? -ne 0 ]; then
    #     echo "scrape_gasprice.py failed again. Exiting."
    #     exit 1
    # fi
fi

# Run the second Python script
echo "Running clean_data.py..."
python3 ./clean_data.py

# Check if the second script ran successfully
if [ $? -ne 0 ]; then
    echo "clean_data.py failed. Exiting."
    exit 1
fi

# Run the third Python script
echo "Running visualization.py..."
python3 ./visualization.py

# Check if the third script ran successfully
if [ $? -ne 0 ]; then
    echo "visualization.py failed. Exiting."
    exit 1
fi

echo "All scripts executed successfully!"

echo "Pushing to GasPriceAnalysis GitHub..."
git pull
git add output
git add data/cleaned_gas_prices.xlsx
git add data/gas_prices.xlsx
git add log
git commit -m "auto-update new data"
git push 

echo "Pushing to QAQ0701.github.io ..."
cd /Users/o_o/Documents/GitHub/
echo "Copying files to QAQ0701.github.io..."
cp -R GasPriceAnalysis/output/* QAQ0701.github.io/output
cd QAQ0701.github.io
git pull
git add .
git commit -m "auto-update gasbuddy graphs"
git push

echo "Updated graphs and pushed to https://qaq0701.github.io/visualization.html"
