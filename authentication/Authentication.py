from CollegeManagement.connection import createConnection


def checkCredential(id,password,table):
    try:
        db,cmd=createConnection()
        q=f"select {table}id,password from {table} where emailid='{id}'"
        cmd.execute(q)
        count=cmd.rowcount
        db.close()
        if(count==0):
            return False,-1
        else:
            result=cmd.fetchone()
            # res=bcrypt.checkpw(password,str(result[1]).encode())
            res=password==result['password']
            if(res):
                return True,result[f"{table}id"]
            else:
                return False,-1
    except Exception as e:
        print("Error dataBase"+str(e))
        return False,0
def FetchData(id,table):
    try:
        q=f"select * from {table} where {table}id={id}"
        db,cmd=createConnection()
        cmd.execute(q)
        data=cmd.fetchone()
        db.close()
        data.pop('password')
        data=isClubMember(data,id,table)
        return True,data
    except Exception as e:
        print(e)
        return False,[]
def isClubMember(data:dict,id,status):
    try:
        if(bool(data['clubmember'])):
            l=['clubid', 'clubname', 'hoc', 'hocid', 'clubcode', 'clublogo', 'numberofmember', 'goal', 'status','clubmemberid']
            db, cmd = createConnection()
            q = f"select p.*,s.* from club s,collegeclub p where s.memberid={id} and s.memberstatus='{status}' and s.clubcode=p.clubid"
            cmd.execute(q)
            dataClub = cmd.fetchone()
            if(dataClub):
            # dataClub = dict(zip(l, dataClub))
                data.update(dataClub)
            db.close()
        return data
    except Exception as e:
        print(e)
        return data