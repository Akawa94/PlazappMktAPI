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

@app.route("/mkt/user_test")
def user_test():
    try:
        cur.execute("SELECT * FROM users")
        q_result = cur.fetchall()
        if (len(q_result)==0):
            return jsonify([])
        else:
            return jsonify(q_result)
    except Exception as e:
        print(e)
        return jsonify([])

def passwordCreation():
    """
    We will create a new 8 digit password
    """
    abcd = "abcdefghijklmnopqrstuvwyzABCDEFGHIJKLMNOPQRSTUVWYZ"
    newPass = ""
    for i in range(0,8):
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
    cur.execute("SELECT password FROM users WHERE id='"+user_id+"'")
    q_result = cur.fetchall()
    if (len(q_result)>0):
        return q_result[0][0]
    else:
        return '-1'

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

    final_result = {}
    final_result['categories'] = []
    final_result['stores'] = []
    final_result['products'] = []
    final_result['user_data'] = data
    return jsonify(final_result)
