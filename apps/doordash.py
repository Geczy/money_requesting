import streamlit as st
import pandas as pd
import numpy as np # for nan

def name_maker(my_names):
    '''
    Formats user inputed names, and appends other info like total, subtotal, delivery fee, etc.
    '''
    my_names = my_names.split(',')
    # format input to remove space and make it all lowercase
    names = [n.lower().strip() for n in my_names]
    only_names = names.copy()
    names += ['subtotal','tax','delivery','service','tip','total']
    names = tuple(names)
    return names, only_names

def receipt_formatter(receipt, names):
    '''
    Eliminates all the extra fluff, retaining just the names and appropriate prices
    '''
    text_str = pd.Series(receipt.split('\n')) # split by new line

    # find where each name occurs to infer what belongs to them
    names_dict = {}
    for loc, string in text_str.iteritems():
        for name in names:
            if (name in string) and (name != 'total'): # to keep total at bottom of dict
                names_dict[name] = loc
            if ('total' == name) and ('subtotal' not in string) and ('total' in string):
                names_dict['total'] = loc
    keys = list(names_dict.keys())
    # get range of locs, where loc1 is the already gotten loc
    # and loc2 is the next keys value
    names_range = {}
    for i in range(len(keys)):
        name = keys[i]
        loc1 = names_dict[name]
        try:
            next_name = keys[i+1]  
            loc2 = names_dict[next_name] # loc of next name
        except:
            loc2 = len(keys) # this is total
        names_range[name] = [loc1, loc2]
    
    # assign each line to a name
    names_str_items = {}
    for name, nums in names_range.items():
        names_str_items[name] = text_str.loc[nums[0]:nums[1]-1]
        if ('total' in name) and ('subtotal' not in name):
            names_str_items[name] = text_str.loc[nums[0]:] # previous formula wouldn't work for total, 
                                                           # since it SHOULD be the last in series
    # extract only the prices from each line
    names_prices = {}
    for name, data in names_str_items.items():
        my_data = data.str.extract('\$(\d+\.\d+)')
        my_data = my_data.dropna()[0]
        names_prices[name] = list(pd.to_numeric(my_data))
        
    return names_prices

def sanity_check(names_prices):
    '''
    Confirms with the user that the calculated total is equal to the actual total.
    If True, script continues.
    If False, script stops.
    '''
    #### SANITY CHECK ####
    total = 0
    for k, v in names_prices.items():
        if k not in 'subtotal':
            total += sum(names_prices[k])

    st.info(f"The total paid was __${round(total,2)}__, is this correct?")
    sanity_check = st.radio("",["Yes","No"])
    if "no" in sanity_check.lower():
        st.warning("Sorry about that, try the manual or OCR options.")
        st.write("Here's what I found:")
        # show our output for future feedback
        # Let user edit the df as needed!
        max_len = 0
        for k,v in names_prices.items():
            if len(v) > max_len:
                max_len = len(v)
        for k,v in names_prices.items():
            for i in range(max_len):
                if len(v) < max_len:
                    v.append(np.nan) # to make all lists same size for df
        cols = []
        for i in range(max_len): # give names to columns
            cols.append(f'Item {i+1}')
        food_feedback = pd.DataFrame(names_prices).T
        food_feedback.columns = cols
        st.table(food_feedback)
        st.stop()
        letsgo = False
    else:
        letsgo = True
        return
        
    return letsgo
def receipt_for_machine(my_dict, description, only_names):
    '''
    Formats a dictionary of prices to be compatible with the rest of the payme script
    '''
    fees_input = 0
    tax_input = 0
    tip_input = 0
    receipt_input = ''
    for name, values in my_dict.items():
        if name not in only_names: # then its fees and stuff
            if not values: # if the list is empty
                pass # dont add anything to counters
            else:
                if (name == 'service') or (name == 'delivery'):
                    fees_input += values[0]
                if name == 'tax':
                    tax_input += values[0]
                if name == 'tip':
                    tip_input += values[0]
        else:
            if not values:
                st.error("Tell Pete a name is missing prices.")
                st.info("Try manual mode!")
                st.stop()
            else:
                # account for promo in sum
                standardized = f"{name}: {sum(values)}"
                receipt_input += standardized
    return_me = {}   
    return_me['description'] = description
    return_me['receipt_input'] = receipt_input
    return_me['fees_input'] = fees_input
    return_me["tax_input"] = tax_input # always 0 in mexico, VAT is included
    return_me['tip_input'] = tip_input
    
    return return_me
    


def app():
    '''
    Main region of doordash parser
    '''
    import base64
    with st.beta_expander("How To"):
        col1,col2 = st.beta_columns(2)
        with col1:
            st.write("""
            1. Copy and paste the entire contents of DoorDash receipt from *Order Details* at the top to the total at the bottom.
            2. Follow the prompts
            """)
        with col2:
            st.markdown("![DoorDash copy instructions](https://github.com/pomkos/payme/raw/main/images/copy_dd.gif)")
    ### GUI ###
    description = st.text_input("(Optional) Description, like the restaurant name")
    receipt = st.text_area("Paste the entire receipt from D below, including totals and fees")
    receipt = receipt.lower()
    # receipt = receipt.replace(',','')
    if receipt:
        my_names = st.text_input("Add names below, separated by a comma. Ex: peter, Russell")
    if not receipt:
        st.stop()
    if not my_names:
        st.stop()
        
    # Get the names, adds additional variables like total, tip, fees, etc
    names, only_names = name_maker(my_names)
    
    # Assign prices to each variable, eliminate extras
    names_prices = receipt_formatter(receipt, names)
    # Confirm with user total is correct
    sane = sanity_check(names_prices)
    if sane == False:
        st.stop()
    # standardize output for rest of script    
    return_me = receipt_for_machine(names_prices, description, only_names)
    return return_me