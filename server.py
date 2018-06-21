from flask import Flask, jsonify
import psycopg2
# Import smtplib for the actual sending function
import smtplib
import random
import sys
import json
import requests

app = Flask(__name__)
conn = psycopg2.connect("dbname=plaza_app user=inf227")
cur = conn.cursor()





def passwordCreation():
    """
    We will create a new 8 digit password
    """
    abcd = "abcdefghijklmnopqrstuvwyzABCDEFGHIJKLMNOPQRSTUVWYZ"
    newPass = ""
    for i in range(0,5):
        newPass += str(random.randint(0,10))
        newPass += str(abcd[random.randint(0,len(abcd)-1)])
    return newPass
    
def passwordHash(newPass):
    """
    Will retrieve user_id with encrypted newPass from BD by using rails service
    """
    dummy_email = "mkt.recovery.email@pucp.pe"
    cur.execute("SELECT * FROM users WHERE email='"+dummy_email+"'")
    q_result = cur.fetchall()
    if(len(q_result)>0):
        cur.execute("DELETE FROM users WHERE email='"+dummy_email+"'")
        conn.commit()
    values = {}
    values["user"]={}
    values["user"]["email"] = dummy_email
    values["user"]["password"] = newPass
        
    res = requests.post('http://200.16.7.150:8083/api/v1/users',
                 json=values)
    responseDict = res.json()
    print(responseDict)
    if 'error' not in list(responseDict.keys()):
        print(responseDict["user"]["id"])
        return int(responseDict["user"]["id"])
    return -1

def retrieveEncryptedPass(user_id):
    cur.execute("SELECT encrypted_password FROM users WHERE id='"+str(user_id)+"'")
    q_result = cur.fetchall()
    if (len(q_result)>0):
        return q_result[0][0]
    else:
        return '-1'
    
def getName(preferences, p_id):
    for pref in preferences:
        if pref[0] == p_id:
            return pref[1]
    return 'None found'
    
@app.route("/mkt/recommended_categories/<user_id>")
def recommended_categories(user_id):
    range_top = 100
    range_step = 10
    cur.execute("select store_category_id from reviewed_products where user_id="+str(user_id)+"order by created_at desc")
    user_searches = cur.fetchall()
    cur.execute("select distinct store_category_id from preference_store_categories where user_id="+str(user_id)) 
    user_current_preferences = cur.fetchall()
    print(user_current_preferences)
    cur.execute("select id,name from store_categories")
    all_preferences = cur.fetchall()
    pref_dict = {}
    for pref in all_preferences:
        pref_dict[pref[0]]=0
    for pref in user_current_preferences:
        pref_dict[pref[0]]+=10
    for i in range(0,range_top,range_step):
        pref_range = user_searches[i:range_step]
        if (len(pref_range)==0):
            break
        for pref in pref_range:
            pref_dict[pref[0]]+=int(int(range_top/range_step)-i)
    d = pref_dict
    final_results = [(k, d[k]) for k in sorted(d, key=d.get, reverse=True)][:5]    
    print(final_results)
    final_dict = []
    for e in final_results:
        if (e[1] <= 0):
            continue
        final_dict.append({
            'name': getName(all_preferences,e[0]),
            'id': e[0],
            'score': e[1]
        })
    # transform answer same as reached by admin services
    return jsonify(final_dict)

@app.route("/mkt/recommended_categories_all/<email>")
def recommended_categories_all(email):
    # search for user
    cur.execute("select id from users where email='"+email+"'")
    q_results = cur.fetchall()
    if (len(q_results)==0):
        return jsonify([])
    user_id = q_results[0][0]
    range_top = 100
    range_step = 10
    cur.execute("select store_category_id from reviewed_products where user_id="+str(user_id)+"order by created_at desc")
    user_searches = cur.fetchall()
    cur.execute("select distinct store_category_id from preference_store_categories where user_id="+str(user_id)) 
    user_current_preferences = cur.fetchall()
    print(user_current_preferences)
    cur.execute("select id,name from store_categories")
    all_preferences = cur.fetchall()
    pref_dict = {}
    for pref in all_preferences:
        pref_dict[pref[0]]=0
    for pref in user_current_preferences:
        pref_dict[pref[0]]+=10
    for i in range(0,range_top,range_step):
        pref_range = user_searches[i:range_step]
        if (len(pref_range)==0):
            break
        for pref in pref_range:
            pref_dict[pref[0]]+=int(int(range_top/range_step)-i)
    d = pref_dict
    final_results = [(k, d[k]) for k in sorted(d, key=d.get, reverse=True)]    
    print(final_results)
    final_dict = []
    for e in final_results:
        final_dict.append({
            'name': getName(all_preferences,e[0]),
            'id': e[0],
            'score': e[1]
        })
    # transform answer same as reached by admin services
    return jsonify(final_dict)


@app.route("/mkt/email_recovery/<email>")
def email_recovery(email):
    try:
        print(email)
        cur.execute("SELECT * FROM users WHERE email='"+email+"'")
        #print(cur.description)
        # can only do fetchall once
        q_result = cur.fetchall()
        print(len(q_result))
        if (len(q_result) == 0):
            return jsonify([])
        else:
            q_result = q_result[0]
    except Exception as e:
        print("Unexpected error:", e)
        return jsonify([])
        
    newPass = passwordCreation()
    user_id = passwordHash(newPass)
    if (user_id<0):
        return jsonify([])
    
    newEncryptedPass = retrieveEncryptedPass(user_id)
    if (newEncryptedPass == '-1'):
        return jsonify([])
    
    cur.execute("UPDATE users SET encrypted_password='"+newEncryptedPass+"' WHERE email='"+email+"'")
    conn.commit()
    print(cur.rowcount)
    return jsonify({'newPass': newPass})

@app.route("/mkt/password_change/<userid>/<password>")
def password_change(userid,password):
    user_id = passwordHash(password)
    if (user_id) < 0:
        return jsonify([])
    newEncryptedPass = retrieveEncryptedPass(user_id)
    if (newEncryptedPass == '-1'):
        return jsonify([])
    cur.execute("UPDATE users SET encrypted_password='"+newEncryptedPass+"' WHERE id='"+userid+"'")
    conn.commit()
    return jsonify({'success':'success'})
        

@app.route("/mkt/user_vector/<user_id>")
def user_vector(user_id):
    try:
        print(int(user_id))
        cur.execute('SELECT * FROM users WHERE id='+user_id)
        print(cur.description)
        q_result = cur.fetchall()[0]
    except:
        print("Unexpected error:", sys.exc_info()[0])
        return jsonify([])
    user_data = [str(x) for x in q_result]
    cur.execute("SELECT * FROM users LIMIT 0")
    user_keys = [desc[0] for desc in cur.description]
    data={}
    for i in range(0,len(user_keys)):
        data[user_keys[i]] = user_data[i]
    # will retrieve users that have preferences in common
    # per each category, we will retrieve users with similar amount of prefered
    # items, and prefered stores
    
    
    # will pondere these users preferences.

    # according to these ponderations,
    # we will take the top 10 count for each:
    # stores, products and categories.

    # these will be feed into a subsequence of funcs
    # which will return a series of ids for each table
    ffs = []
    ffs.append(1)
    final_result = {}
    final_result['categories'] = []
    final_result['stores'] = []
    final_result['products'] = []
    final_result['user_data'] = data
    return jsonify(final_result)




