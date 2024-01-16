import streamlit as st
import numpy as np
import numpy_financial as npf
import pandas as pd
import math
from operator import itemgetter
import copy
import fnmatch


page_title = 'Savings Optimiser'


st.set_page_config(
    page_title=page_title,
    page_icon=':money_with_wings:',
    layout='wide'
)






st.write('# '+page_title)


with st.expander('How to use this calculator'):
    """This calculator will show you how best to distribute your savings 
    (a singular lump, a monthly amount, or a combination of the two) across 
    whatever savings accounts are available to you"""
    """It will also take into account whether your savings interest is taxable (by 
    declaring whether an account is an ISA or not) and your personal savings allowance. 
    It may be that a taxable account becomes less lucrative once you have exceeded your PSA"""
    '''You will be shown an "adjusted interest rate", which is the interest rate of the account once 
    you deduct any tax that would be incurred on that account. For example, a taxable account earning 10% 
    will effectively only earn 8% if you reach your PSA and pay 20% income tax'''
    """By entering monthly or total account deposit limits, you will be able to include accounts such as 
    regular savers or accounts which stop paying high interest above a certain threshold. You can also 
    use the total account limit on ISA accounts to limit deposits to your ISA allowance"""
    """This is not suitable for mixing with LISAs or stocks and shares ISAs, as it will not include the LISA 
    bonus and stocks and shares returns are not fixed"""
    """This could be used for comparing mortgage overpayments, as they can be treated as an ISA account (because overpayments are tax free) with a 
    deposit limit equal to your overpayment allowance and an interest rate equal to the mortgage rate. While 
    the results will be accurate from a return on investment point of view, note that there are other considerations 
    with mortgage overpayments such as liquidity which should be considered. See 
    [here](https://ukpersonal.finance/mortgage-overpayments-vs-investments) for more details"""
    """This calculator will not take into account monthly compounding and will only show 12 months of results. Realistically 
    monthly compounding will make a minimal difference, and many accounts either mature or pay interest yearly"""
    """The results are calculated on a month by month basis, so the calculator will only know when you have exceeded your PSA 
    once your total taxable interest exceeds your PSA (i.e it cannot extrapolate to when you will exceed you PSA, nor does it 
    know on what day in a particular you exceed your PSA). As such you may exceed your PSA by a small amount before being directed to 
    redirect funds to higher paying ISAs. This will result in a minimal amount of interest being taxable if it occurs. If you 
    are adamant that none of your interest must be taxable for whatever reason, this calculator may not be suitable depending on 
    the results you get. There is little reason to be concerned about breaching the PSA by a small amount, as the cost will be extremely 
    small and it is unlikely to involve any additional work from you (such as a self-assessment). More info [here](https://www.gov.uk/apply-tax-free-interest-on-savings)"""
    '''This calculator works by looking at what funds you have on a monthly basis (both new deposits and existing funds), and looks at 
    lower interest earning accounts to see if higher interest earning accounts are available to deposit into. A default "current account" 
    will be automatically created to initially house any new funds and will store any funds that cannot be put into a higher interest 
    earning account'''


st.divider()

"""## Savings information"""


lump_sum = st.number_input(
    'Do you have a **lump sum** to put into savings (optional)? (£)',
    0,
    10000000,
    0,
    help='If you do not have a lump sum to save, please enter 0. The lump sum will appear in the first months "Amount to save" column'
)

monthly_deposit = st.number_input(
    'How much do you have to save **each month**? (£)',
    0,
    10000000,
    100
)

personal_allowance = st.number_input(
    'What is your **personal savings allowance**? (£)',
    0,
    1000,
    500,
    500,
    help="""More information about the PSA can be found [here](https://www.moneysavingexpert.com/savings/personal-savings-allowance). 
    Note that your total income used to calculate your PSA includes savings interest. This can be a complicated topic, so if 
    your PSA is not immediatly obvious to you then you should seek support in calculating it. The maximum PSA this claculator will allow is £1000"""
)

if personal_allowance % 500 != 0:
    st.warning("""You entered £{} as your personal savings allowance. PSA should 
               be either £0, £500, or £1000. This calculator will show results 
               based on your entered PSA, but this may be misleading""".format(personal_allowance))
    

entered_tax_rate = st.number_input(
    'What is your **income tax rate**? (%)',
    0,
    100,
    40,
    20,
    help="""This is the tax rate which any interest over your PSA will be taxed at. If you are not sure on your 
    tax rate as it applies to savings you should confirm this before continuing. If you are close to a tax band threshold 
    and will therefore pay some tax at one rate and some at another, this calculator may not be appropriate for you"""
)

if not entered_tax_rate in [20,40,45]:
    st.warning("""You have entered an income tax rate of {}%. Income tax 
               rates are typically 20%/40%/45%. This calculator will show results 
               based on your entered income tax rate, but this may be misleading""".format(entered_tax_rate))


tax_rate = entered_tax_rate / 100.00

if (not (entered_tax_rate == 20 and personal_allowance == 1000)) and (not (entered_tax_rate == 40 and personal_allowance == 500)) and (not (entered_tax_rate == 45 and personal_allowance == 0)):
    st.warning("""You entered a personal savings allowance of £{} and an income tax 
               rate of {}%. Typically the PSA/tax pairings are £1000/20%, £500/40%, £0,45%. This 
               calculator will show results based on your entered values, but this may be misleading""".format(personal_allowance,entered_tax_rate))


st.divider()

"""## Available savings accounts"""




"Enter the details of savings accounts available to you:"
available_accounts_df = st.data_editor(pd.DataFrame(
    {
        'Account name': pd.Series(dtype='str'),
        'Gross Interest Rate': pd.Series(dtype='float'),
        'Monthly Deposit Limit': pd.Series(dtype='int'),
        'Total Deposit Limit': pd.Series(dtype='int'),
        'Is ISA': pd.Series(dtype='bool')
    }),num_rows='dynamic',
    column_config={
        'Account name': st.column_config.TextColumn(
            help="Choose a meaningful name for any accounts you input, as they will be referenced frequently in the results"
        ),
        'Gross Interest Rate': st.column_config.NumberColumn(
            label='Gross Interest Rate (%)',
            format='%.2f%%',
            help="""Enter the gross interest for the account. This calculator will not consider monthly compounding. This 
            rate will be adjusted throughout the year based on yout PSA and tax rate"""
        ),
        "Monthly Deposit Limit": st.column_config.NumberColumn(
            label='Monthly Deposit Limit (£)',
            format='£%.2f',
            help="E.g. a regular saver limit"
        ),
        'Total Deposit Limit': st.column_config.NumberColumn(
            label='Total Deposit Limit (£)',
            format='£%.2f',
            help="E.g. a limit before a savings account reduces its rate, or an ISA which has a limit equal to your remaining ISA allowance"
        ),
        "Is ISA": st.column_config.CheckboxColumn(
            label='Is ISA?',
            help="Is this account an ISA or some other form of non-taxable account (e.g. this could be used for mortgage overpayments)"
        )
    })

nan_columns = available_accounts_df.columns[available_accounts_df.isna().any()].to_list()
name_and_interest = ['Account name','Gross Interest Rate']

if available_accounts_df.shape[0] == 0:
    st.error("Please enter some available savings accounts")
    st.stop()

if [i for i in nan_columns if i in name_and_interest]:
    st.error("Every account must have a name and gross interest rate")
    st.stop()

if not pd.Series(available_accounts_df['Account name']).is_unique:
    st.error("Every account must have a unique name")
    st.stop()

if "current account" in list(map(lambda x: x.lower(),available_accounts_df['Account name'])):
    st.error('''Please enter an account name other than "Current account". A default account 
               named "Current account" will be created for you to store any amount that cannot be stored in any other account''')
    st.stop()

available_accounts_df.loc[available_accounts_df.shape[0]] = ['Current account',0.00,np.nan,np.nan,False]



results_df = pd.DataFrame(
    {
        'Month': np.arange(12) + 1
    }
)

for i in np.arange(12):
    if i == 0:
        results_df.at[i,'Amount to save'] = lump_sum + monthly_deposit
    else:
        results_df.at[i,'Amount to save'] = monthly_deposit


list_of_adjusted_interests = []


for idx,i in enumerate(available_accounts_df['Account name']):
    column_header = i + ' Adjusted Interest Rate'
    adjust_interest = available_accounts_df.iloc[idx,available_accounts_df.columns.get_loc('Gross Interest Rate')] * (1 - (0 if available_accounts_df.iloc[idx,available_accounts_df.columns.get_loc('Is ISA')] else tax_rate) if personal_allowance == 0 else 1)
    results_df.at[0,column_header] = adjust_interest
    list_of_adjusted_interests.append(adjust_interest)



temp_monthly_deposit = results_df.loc[0,'Amount to save']



for idx, i in sorted(enumerate(list_of_adjusted_interests), key=itemgetter(1),reverse=True):
    column_header = available_accounts_df.iloc[idx,available_accounts_df.columns.get_loc('Account name')] + ' Amount'
    monthly_deposit_limit = available_accounts_df.iloc[idx, available_accounts_df.columns.get_loc('Monthly Deposit Limit')]
    total_deposit_limit = available_accounts_df.iloc[idx, available_accounts_df.columns.get_loc('Total Deposit Limit')]
    amount_to_deposit =  np.nanmin([temp_monthly_deposit,monthly_deposit_limit,total_deposit_limit])
    temp_monthly_deposit = max(0, temp_monthly_deposit - amount_to_deposit)
    results_df.at[0,column_header] = amount_to_deposit



for idx, i in enumerate(available_accounts_df['Account name']):
    column_header = i + ' Monthly deposit'
    amount = results_df.loc[0,i + ' Amount']
    interest = amount / 100 / 12 * results_df.loc[0,i+ ' Adjusted Interest Rate']
    results_df.at[0,column_header] = amount


for idx, i in enumerate(available_accounts_df['Account name']):
    column_header = i + ' Monthly Interest'
    amount = results_df.loc[0,i + ' Amount']
    interest = amount / 100 / 12 * results_df.loc[0,i+ ' Adjusted Interest Rate']
    results_df.at[0,column_header] = interest


first_total_monthly_taxed_interest = 0.00
first_total_monthly_isa_interest = 0.00


for idx, i in enumerate(available_accounts_df['Account name']):
    if available_accounts_df.iloc[idx,available_accounts_df.columns.get_loc('Is ISA')]:
        first_total_monthly_isa_interest += results_df.loc[0,i+' Monthly Interest']
    else:
        first_total_monthly_taxed_interest += results_df.loc[0,i+' Monthly Interest']


results_df.at[0,'Total Monthly taxed Interest'] = first_total_monthly_taxed_interest
results_df.at[0,'Total Monthly ISA Interest'] = first_total_monthly_isa_interest
results_df.at[0,'Total Monthly Interest'] = first_total_monthly_isa_interest + first_total_monthly_taxed_interest

results_df.at[0,'Total Running taxed Interest'] = first_total_monthly_taxed_interest
results_df.at[0,'Total Running ISA Interest'] = first_total_monthly_isa_interest
results_df.at[0,'Total Running Interest'] = first_total_monthly_isa_interest + first_total_monthly_taxed_interest



for i in range(1,12):
    list_of_remaining_deposits = {} 
    list_of_account_names = {}
    for j in range(available_accounts_df.shape[0]):
        account_name = available_accounts_df.iloc[j,available_accounts_df.columns.get_loc('Account name')]
        monthly_deposit_limit = available_accounts_df.iloc[j,available_accounts_df.columns.get_loc('Monthly Deposit Limit')]
        total_deposit_limit = available_accounts_df.iloc[j,available_accounts_df.columns.get_loc('Total Deposit Limit')] - results_df.loc[i-1,account_name+' Amount']
        list_of_remaining_deposits[j] = [monthly_deposit_limit,total_deposit_limit]
        list_of_account_names[j] = account_name


    list_of_adjusted_interests = {}
    for idx,j in enumerate(available_accounts_df['Account name']):
        column_header = j + ' Adjusted Interest Rate'
        adjust_interest = available_accounts_df.iloc[idx,available_accounts_df.columns.get_loc('Gross Interest Rate')] * (1 - (0 if available_accounts_df.iloc[idx,available_accounts_df.columns.get_loc('Is ISA')] else tax_rate) if results_df.loc[i-1,'Total Running taxed Interest'] >= personal_allowance else 1)
        results_df.at[i,column_header] = adjust_interest
        list_of_adjusted_interests[idx] =  adjust_interest


    temp_monthly_deposit = results_df.loc[i,'Amount to save']

    list_of_current_balances = {}
    for idx, j in enumerate(available_accounts_df['Account name']):
        current_balance = results_df.loc[i-1,j+' Amount'] + (0 if not j == 'Current account' else temp_monthly_deposit)
        list_of_current_balances[idx] =  current_balance

    list_of_new_balances = copy.deepcopy(list_of_current_balances)

    for j,k in sorted(list_of_adjusted_interests.items(), key=lambda x: x[1]):
        current_balance = list_of_current_balances[j]
        for l,m in sorted(list_of_adjusted_interests.items(), key=lambda x: x[1], reverse=True):
            remaining_monthly_deposit = list_of_remaining_deposits[l][0]
            remaining_total_depost = list_of_remaining_deposits[l][1]
            amount_to_deposit = np.nanmin([current_balance,remaining_monthly_deposit,remaining_total_depost])
            if m > k:
                list_of_new_balances[l] += amount_to_deposit
                list_of_new_balances[j] -= amount_to_deposit
                current_balance -= amount_to_deposit
                list_of_remaining_deposits[l][0] -= amount_to_deposit
                list_of_remaining_deposits[l][1] -= amount_to_deposit

    total_monthly_isa_interest = 0.0
    total_monthly_taxed_interest = 0.0


    for j, k in list_of_new_balances.items():
        results_df.at[i,list_of_account_names[j] + ' Amount'] = k
        results_df.at[i,list_of_account_names[j] + ' Monthly deposit'] = k - list_of_current_balances[j] + (temp_monthly_deposit if list_of_account_names[j] == 'Current account' else 0)
        monthly_interest = k * list_of_adjusted_interests[j] / 100 / 12
        results_df.at[i,list_of_account_names[j] + ' Monthly Interest'] = monthly_interest
        if available_accounts_df.iloc[j,available_accounts_df.columns.get_loc('Is ISA')]:
            total_monthly_isa_interest += monthly_interest
        else:
            total_monthly_taxed_interest += monthly_interest

    results_df.at[i,'Total Monthly taxed Interest'] = total_monthly_taxed_interest
    results_df.at[i,'Total Monthly ISA Interest'] = total_monthly_isa_interest
    results_df.at[i,'Total Monthly Interest'] = total_monthly_isa_interest + total_monthly_taxed_interest


    results_df.at[i,'Total Running taxed Interest'] = results_df.loc[0:i,'Total Monthly taxed Interest'].sum()
    results_df.at[i,'Total Running ISA Interest'] = results_df.loc[0:i,'Total Monthly ISA Interest'].sum()
    results_df.at[i,'Total Running Interest'] = results_df.loc[0:i,'Total Monthly Interest'].sum()


st.divider()

"""## Results"""


with st.expander('Show table options'):   
    show_current_account = st.toggle(
        "Show default current account?",
        help='''A default "Current account" is automatically created to store any savings 
        which cannot be deposited to any other accounts. It is likely this account will not be needed, as 
        there will likely be a savings account available which is a better choice than a current account. Toggle 
        here to show/hide values for this "current account"'''
    )

    show_adjusted_interest_rates = st.toggle(
        'Show adjusted interest rates?',
        help='''Toggle here to show/hide the interest rate an account earns (taking in to account tax)'''
    )

    show_interest = st.toggle(
        'Show monthly and running total interest amounts?',
        help='''Toggle here to show/hide how much interest is earned by each savings account. You will also be 
        shown monthly totals for taxable/non-taxable interest, and a running total of taxable/non-taxable interest'''
    )

    show_amounts = st.toggle(
        'Show total running account balances?',
        True
        ,help='''Toggle here to show/hide what the account balance should be for each saving account each month'''
    )





for i in list(results_df):
    if "Current account" in i and (not show_current_account):
        results_df.drop(i, axis=1, inplace=True)

for i in list(results_df):
    if "Adjusted Interest Rate" in i and (not show_adjusted_interest_rates):
        results_df.drop(i, axis=1, inplace=True)

for i in list(results_df):
    if "Interest" in i and (not show_interest) and (not "Adjusted Interest Rate" in i):
        results_df.drop(i, axis=1, inplace=True)

for i in list(results_df):
    if " Amount" in i and (not show_amounts):
        results_df.drop(i, axis=1, inplace=True)




"""(Hover over a column header if you are not sure what it showing)"""




format_dict = {}


for i in list(results_df):
    if "Adjusted Interest Rate" in i:
        format_dict[i] = lambda x : '{:.2f}%'.format(x)
    elif "Month" != i:
        format_dict[i] = lambda x : '£{:,.2f}'.format(x)
    

        
column_config_dict = {}

for i in list(results_df):
    if "Adjusted Interest Rate" in i:
        column_config_dict[i] = st.column_config.NumberColumn(help="This is what the interest rate on the account will be after factoring in tax")
    elif "Running" in i:
        column_config_dict[i] = st.column_config.NumberColumn(help="Cumulative interest from month 1 to the month shown")
    elif "Interest" in i:
        column_config_dict[i] = st.column_config.NumberColumn(help="How much interest will be earned this month")
    elif "Monthly deposit" in i:
        column_config_dict[i] = st.column_config.NumberColumn(help="How much should be deposited/withdrawn in this account this month")
    elif "Amount to save" in i:
        column_config_dict[i] = st.column_config.NumberColumn(help="How much is available to be saved this month. Month 1 will include any lump sums")
    elif "Amount" in i:
        column_config_dict[i] = st.column_config.NumberColumn(help="What the total balance will be in this account this month")


        




st.dataframe(results_df.style.format(format_dict)
,hide_index=True,
column_config=column_config_dict
)
