from flask import Flask, request, url_for, redirect,render_template, flash
import os,sys
from threading import Thread
import urllib, copy, json, datetime
import xml.etree.ElementTree as ET
import dateutil.parser
import pygal
import matplotlib.pyplot as plt
import tornado
import urllib,base64
import StringIO


template_dir=''
app = Flask(__name__,template_folder=template_dir,static_folder=template_dir)
app.config['DEBUG'] = False


@app.route('/')
def index():
    global entryState
    entryState=True
    return render_template('index.html')



@app.route('/machstat_machines', methods=['GET','POST'])
def machstat_machines():
    global entryState
    global MTCagentList
    global urlValid
    if request.method=='POST':
        attempted_add_machine=request.form['add_machine']
    try:
        urllib.urlopen(attempted_add_machine)
        currentRequest=copy.deepcopy(attempted_add_machine)
        
        with open('config2.json','r') as g:
            config=json.load(g)
        config['request']=str(currentRequest)

        agent=urllib.urlopen(currentRequest).read()
        root=ET.fromstring(agent)
        if len(root.tag.split('}')[0])>1:
            xmlns=root.tag.split('}')[0]+'}'
        else:
            xmlns=''
        machineName=root.findall('.//'+xmlns+'DeviceStream')[0].attrib['name']+':'+root.findall('.//'+xmlns+'DeviceStream')[0].attrib['uuid']
        _buffer=root[0].attrib['bufferSize']
        if [machineName,currentRequest,xmlns,_buffer] not in MTCagentList:
            MTCagentList.append([machineName,currentRequest,xmlns,_buffer])
        config['machines']=MTCagentList
        
        with open('config2.json','w') as f:
            json.dump(config,f)

        urlValid=True
        entryState=False
        return render_template("machstat_machines.html",MTCagentList=MTCagentList, urlValid=urlValid)
    except:
        if entryState==True and urlValid==None:
            urlValid=True
            entryState=False
            return render_template("machstat_machines.html",MTCagentList=MTCagentList, urlValid=urlValid)
        if entryState==True and urlValid==True:
            urlValid=True
            entryState=False
            return render_template("machstat_machines.html",MTCagentList=MTCagentList, urlValid=urlValid)
        elif entryState==False and urlValid==True:
            urlValid=False
            return render_template("machstat_machines.html",MTCagentList=MTCagentList, urlValid=urlValid)
        elif urlValid==False:
            return render_template("machstat_machines.html",MTCagentList=MTCagentList, urlValid=urlValid)
        elif urlValid==True:
            urlValid=False
            return render_template("machstat_machines.html",MTCagentList=MTCagentList, urlValid=urlValid)

@app.route('/machstat_machines/<id>')
def machine(id):
    with open('config2.json','r') as f:
        config=json.load(f)
    for i,x in enumerate(config['machines']):
        if x[0]==id:
            break
    if int(str(config['machines'][i][3]))<100:
        samplestream='http://'+str(config['machines'][i][1]).split('/')[-2]+'/sample?count='+str(config['machines'][i][3])
    else:
        samplestream='http://'+str(config['machines'][i][1]).split('/')[-2]+'/sample?count=100'

    root=urllib.urlopen(samplestream).read()
    root=ET.fromstring(root)

    creationTime=root[0].attrib['creationTime']
    if creationTime[-1]=='Z':
        creationTime=creationTime[:-1]
    creationTime=dateutil.parser.parse(creationTime)

    
    y=[]
    """
    for x in root.findall(".//"+config['machines'][i][2]+"SpindleSpeed"):
        if x.attrib['name']=='Sspeed' and str(x.text)!='UNAVAILABLE':
            if x.attrib['timestamp'][-1]=='Z':
                time=x.attrib['timestamp'][:-1]
            else:
                time=x.attrib['timestamp']
            y.append([dateutil.parser.parse(x.attrib['timestamp']),float(x.text)])

    for x in root.findall(".//"+config['machines'][i][2]+"RotaryVelocity"):
        if x.attrib['name']=='Srpm' and str(x.text)!='UNAVAILABLE':
            if x.attrib['timestamp'][-1]=='Z':
                time=x.attrib['timestamp'][:-1]
            else:
                time=x.attrib['timestamp']
            y.append([dateutil.parser.parse(time),float(x.text)])
    """
    rpm=y
    
    
    root_current=str(config['machines'][i][1])
    root_current=urllib.urlopen(root_current).read()
    root_current=ET.fromstring(root_current)
    
    machine_name=id;
    try:
        powerState=root_current.findall(".//"+config['machines'][i][2]+"PowerState")[0].text
    except:
        powerState="ON"
    
    if powerState=="OFF":
        execution="OFF"
    else:
        execution=root_current.findall(".//"+config['machines'][i][2]+"Execution")[0].text
        
    estop=root_current.findall(".//"+config['machines'][i][2]+"EmergencyStop")[0].text
    prog=root_current.findall(".//"+config['machines'][i][2]+"Program")[0].text
    if len(root_current.findall(".//"+config['machines'][i][2]+"PartCount")[0].text)>0:
        partCount=root_current.findall(".//"+config['machines'][i][2]+"PartCount")[0].text
    else:
        partCount="NA"
        
    MTCagentList=config['machines']

    try:
        atime=0
        ctime=0
        yltime=0
        for x in root_current.findall(".//"+config['machines'][i][2]+"AccumulatedTime"):
            if x.attrib['dataItemId']=="Spindle_Time":
                atime=int(str(x.text))
                ctime=0.7*atime
                for x in root_current.findall(".//"+config['machines'][i][2]+"Availability"):
                    t2=x.attrib['timestamp'][:-1]
                    t2=dateutil.parser.parse(t2)
                    yltime=(creationTime-t2).seconds

        for x in root_current.findall(".//"+config['machines'][i][2]+"AccumulatedTime"):
            if x.attrib['dataItemId']=="atime":
                atime=int(str(x.text))
            if x.attrib['dataItemId']=="ctime":
                ctime=int(str(x.text))
            if x.attrib['dataItemId']=="yltime":
                yltime=int(str(x.text))

            
        if yltime==0:
            raise Exception
    except:
        atime=5
        ctime=3
        yltime=12
            

    labels = 'ACTIVE:\ncut', 'ACTIVE:\nprep', 'IDLE'
    sizes = [float(ctime)/float(yltime)*360,float(atime-ctime)/float(yltime)*360,float(yltime-atime)/float(yltime)*360]
    colors = ['green', 'yellowgreen', 'gold'] 
    plt.clf()
    fig=''
    # Plot
    fig=plt.gcf()

    imgdata=StringIO.StringIO()
    plt.title('Execution State Pie-Chart')
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', shadow=True, startangle=140)
    #lgd=plt.legend(bbox_to_anchor=(0.83, 1.15))
    plt.axis('equal')
    
    plt.tight_layout()
    fig.savefig(imgdata,format='png')
    imgdata.seek(0)
    uri = 'data:image/png;base64,' + urllib.quote(base64.b64encode(imgdata.buf))
    #fig.savefig('piechart.png') bbox_extra_artists=(lgd,), bbox_inches='tight')
    
    

    utilization=int(float(ctime)/int(yltime)*100)
    utilization=str(int(utilization))+' %'

    
    
    return render_template("visualization.html",**locals())
    
    
if __name__=="__main__":
    with open('config2.json','w') as f:
        json.dump({"request": "", "machines":[]},f)
    _buffer=[]
    MTCagentList=[]
    urlValid=None
    entryState=False
    Thread(target=app.run(debug=False)).start()
