import sys, requests, shutil, datetime
from pathlib import Path
from PySide6.QtWidgets import *
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QFont

API = "http://127.0.0.1:8000"
ACCOUNTS = ["Investor 1 Ledger", "Investor 2 Ledger", "Investor 3 Ledger", "Company Account", "Lending Account", "Interest Ledger", "Additional Charges Ledger", "Company Cash Ledger", "Company Bank Ledger"]

STYLE = """
QMainWindow,QWidget { background:#f4f7fb; color:#17243a; font-family:'Segoe UI'; font-size:10pt; }
#Sidebar { background:#142b4a; }
#Brand { color:white; font-size:19pt; font-weight:700; padding:18px 12px; }
QPushButton#Nav { color:#dce7f5; background:transparent; border:0; text-align:left; padding:13px 18px; border-radius:8px; font-size:10pt; }
QPushButton#Nav:hover,QPushButton#Nav[active="true"] { background:#24476f; color:white; font-weight:600; }
QLabel#PageTitle { font-size:21pt; font-weight:700; color:#172b49; }
QLabel#Muted { color:#718096; }
QFrame#Card { background:white; border:1px solid #e4eaf2; border-radius:12px; }
QLabel#CardTitle { color:#718096; font-size:9pt; }
QLabel#CardValue { color:#17365d; font-size:20pt; font-weight:700; }
QLineEdit,QComboBox,QDateEdit,QDoubleSpinBox,QSpinBox,QTextEdit { background:white; border:1px solid #d6dfeb; border-radius:6px; padding:8px; min-height:20px; }
QPushButton { background:#2163a5; color:white; border:0; border-radius:7px; padding:10px 16px; font-weight:600; }
QPushButton:hover { background:#174d84; }
QPushButton#Secondary { background:#e8eff7; color:#24476f; }
QTableWidget { background:white; border:1px solid #e1e8f0; border-radius:8px; gridline-color:#edf1f6; alternate-background-color:#f7f9fc; }
QHeaderView::section { background:#edf3f9; color:#294565; padding:9px; border:0; font-weight:700; }
QTabWidget::pane { border:0; }
"""

def req(method, path, **kwargs):
    try:
        r=requests.request(method, API+path, timeout=12, **kwargs)
        if not r.ok:
            try: detail=r.json().get('detail',r.text)
            except Exception: detail=r.text
            raise RuntimeError(str(detail))
        return r
    except requests.RequestException as e:
        raise RuntimeError("Finance service is not running. Close and reopen Macha Finance Manager.\n\n"+str(e))

def moneybox(value=0):
    w=QDoubleSpinBox(); w.setRange(0,99999999999); w.setDecimals(2); w.setValue(value); w.setGroupSeparatorShown(True); w.setPrefix("₹ "); return w

def datebox():
    w=QDateEdit(); w.setCalendarPopup(True); w.setDate(QDate.currentDate()); w.setDisplayFormat("dd MMM yyyy"); return w

def make_table(headers):
    t=QTableWidget(0,len(headers)); t.setHorizontalHeaderLabels(headers); t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); t.setAlternatingRowColors(True); t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); t.verticalHeader().setVisible(False); return t

def fill(t, rows, keys):
    t.setRowCount(len(rows))
    for i,row in enumerate(rows):
        for j,key in enumerate(keys):
            v=row.get(key,"")
            if isinstance(v,float): v=f"{v:,.2f}"
            t.setItem(i,j,QTableWidgetItem(str(v if v is not None else "")))

def page(title, subtitle=""):
    w=QWidget(); lay=QVBoxLayout(w); lay.setContentsMargins(26,22,26,22); lay.setSpacing(14)
    h=QLabel(title); h.setObjectName("PageTitle"); lay.addWidget(h)
    if subtitle:
        s=QLabel(subtitle); s.setObjectName("Muted"); lay.addWidget(s)
    return w,lay

def card(title):
    f=QFrame(); f.setObjectName("Card"); l=QVBoxLayout(f); l.setContentsMargins(18,14,18,14)
    a=QLabel(title); a.setObjectName("CardTitle"); b=QLabel("—"); b.setObjectName("CardValue"); l.addWidget(a); l.addWidget(b); return f,b

class Main(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Macha Finance Manager"); self.resize(1440,900); self.setMinimumSize(1120,720)
        root=QWidget(); self.setCentralWidget(root); outer=QHBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        side=QFrame(); side.setObjectName("Sidebar"); side.setFixedWidth(235); sv=QVBoxLayout(side); sv.setContentsMargins(12,12,12,12); sv.setSpacing(5)
        brand=QLabel("MACHA\nFINANCE MANAGER"); brand.setObjectName("Brand"); sv.addWidget(brand)
        self.stack=QStackedWidget(); self.nav=[]
        names=[("Dashboard",self.dashboard_page), ("Customers",self.customer_page), ("Loan Management",self.loan_page), ("Daily Collections",self.collection_page), ("Investor & Company Ledgers",self.ledger_page), ("Fund Transfers",self.transfer_page), ("Interest Ledger",self.interest_page), ("Reports & Backup",self.report_page)]
        for i,(name,builder) in enumerate(names):
            btn=QPushButton(name); btn.setObjectName("Nav"); btn.setProperty("active", i==0); btn.clicked.connect(lambda checked=False,ix=i:self.navigate(ix)); sv.addWidget(btn); self.nav.append(btn)
            self.stack.addWidget(builder())
        sv.addStretch(); foot=QLabel("Local desktop edition\nFinancial records stay on this PC"); foot.setStyleSheet("color:#9fb2c9;padding:12px;"); sv.addWidget(foot)
        outer.addWidget(side); main=QVBoxLayout(); main.setContentsMargins(0,0,0,0); main.setSpacing(0)
        top=QFrame(); top.setStyleSheet("background:white;border-bottom:1px solid #e5ebf2;"); top.setFixedHeight(56); th=QHBoxLayout(top); th.setContentsMargins(24,8,24,8); self.top_label=QLabel("Dashboard"); self.top_label.setStyleSheet("font-weight:600;color:#36516f;"); th.addWidget(self.top_label); th.addStretch(); refresh=QPushButton("Refresh data"); refresh.setObjectName("Secondary"); refresh.clicked.connect(self.refresh_all); th.addWidget(refresh)
        main.addWidget(top); main.addWidget(self.stack); outer.addLayout(main,1)
        self.setStyleSheet(STYLE); self.navigate(0); self.refresh_all()

    def navigate(self, ix):
        self.stack.setCurrentIndex(ix); self.top_label.setText(self.nav[ix].text())
        for i,b in enumerate(self.nav): b.setProperty("active",i==ix); b.style().unpolish(b); b.style().polish(b)
        self.refresh_current()
    def safe(self, fn):
        try: fn()
        except Exception as e: QMessageBox.critical(self,"Macha Finance Manager",str(e))
    def refresh_current(self):
        funcs=[self.load_dashboard,self.load_customers,self.load_loans,self.load_collections,self.load_ledgers,self.load_ledgers,self.load_ledgers,self.load_dashboard]
        self.safe(funcs[self.stack.currentIndex()])
    def refresh_all(self):
        for fn in [self.load_dashboard,self.load_customers,self.load_loans,self.load_collections,self.load_ledgers]:
            try: fn()
            except Exception: pass

    def dashboard_page(self):
        w,l=page("Dashboard","Your lending business at a glance")
        grid=QGridLayout(); self.cards={}
        labels=["Customers","Active Loans","Total Disbursed","Today's Collection","Total Outstanding","Lending Account","Company Account","Interest Ledger"]
        for i,x in enumerate(labels):
            f,v=card(x); self.cards[x]=v; grid.addWidget(f,i//4,i%4)
        l.addLayout(grid); l.addWidget(QLabel("Recent loan portfolio")); self.dtable=make_table(["Loan Number","Customer","Gross Amount","Daily Collection","Collected","Outstanding","Status"]); l.addWidget(self.dtable,1)
        note=QLabel("Loan model: upfront interest deduction with a fixed total collection target. A loan closes only after the full target is collected."); note.setObjectName("Muted"); l.addWidget(note); return w
    def load_dashboard(self):
        d=req("GET","/dashboard").json(); loans=req("GET","/loans").json(); pays=req("GET","/payments").json()
        today=QDate.currentDate().toString("yyyy-MM-dd"); today_amt=sum(float(p['amount']) for p in pays if p['date']==today)
        vals={"Customers":d['customers'],"Active Loans":d['active_loans'],"Total Disbursed":sum(x['net_disbursement'] for x in loans),"Today's Collection":today_amt,"Total Outstanding":d['outstanding'],"Lending Account":d['lending_balance'],"Company Account":self.account_balance("Company Account"),"Interest Ledger":d['interest_ledger_balance']}
        for k,v in vals.items(): self.cards[k].setText(str(v) if isinstance(v,int) else f"₹ {v:,.2f}")
        rows=[]
        for x in loans[:12]: rows.append({"loan_code":x['loan_code'],"customer_name":x['customer_name'],"gross_amount":x['gross_amount'],"daily":x['total_target']/max(1,x['collection_days']),"collected":x['collected'],"outstanding":x['outstanding'],"status":x['status']})
        fill(self.dtable,rows,["loan_code","customer_name","gross_amount","daily","collected","outstanding","status"])
    def account_balance(self,name):
        for x in req("GET","/ledgers").json():
            if x['account']==name:return x['balance']
        return 0

    def customer_page(self):
        w,l=page("Customers","Register customers and maintain a single customer profile")
        box=QFrame(); box.setObjectName("Card"); form=QFormLayout(box); form.setContentsMargins(18,18,18,18)
        self.c_name=QLineEdit(); self.c_dob=datebox(); self.c_phone=QLineEdit(); self.c_pan=QLineEdit(); self.c_aadhaar=QLineEdit(); self.c_aadhaar.setEchoMode(QLineEdit.EchoMode.Password); self.c_doc=QLineEdit(); self.c_docno=QLineEdit()
        for a,b in [("Full name *",self.c_name),("Date of birth",self.c_dob),("Contact number",self.c_phone),("PAN",self.c_pan),("Aadhaar (restricted)",self.c_aadhaar),("Security document type",self.c_doc),("Security document reference",self.c_docno)]: form.addRow(a,b)
        btn=QPushButton("Save customer"); btn.clicked.connect(lambda:self.safe(self.create_customer)); form.addRow(btn); l.addWidget(box)
        self.ct=make_table(["Customer ID","Name","DOB","Phone","PAN","Security Document","Reference","Aadhaar"]); l.addWidget(self.ct,1); return w
    def create_customer(self):
        if not self.c_name.text().strip(): raise RuntimeError("Customer name is required")
        req("POST","/customers",json={"name":self.c_name.text().strip(),"dob":self.c_dob.date().toString("yyyy-MM-dd"),"phone":self.c_phone.text().strip() or None,"pan":self.c_pan.text().strip() or None,"aadhaar":self.c_aadhaar.text().strip() or None,"security_doc_name":self.c_doc.text().strip() or None,"security_doc_number":self.c_docno.text().strip() or None})
        for x in [self.c_name,self.c_phone,self.c_pan,self.c_aadhaar,self.c_doc,self.c_docno]:x.clear()
        self.load_customers(); QMessageBox.information(self,"Saved","Customer profile created.")
    def load_customers(self):
        if hasattr(self,'ct'): fill(self.ct,req("GET","/customers").json(),["customer_code","name","dob","phone","pan","security_doc_name","security_doc_number","aadhaar_masked"])

    def loan_page(self):
        w,l=page("Loan Management","Create loans using the original upfront-interest daily collection model")
        box=QFrame(); box.setObjectName("Card"); form=QFormLayout(box); form.setContentsMargins(18,18,18,18)
        self.l_customer=QComboBox(); self.l_gross=moneybox(100000); self.l_rate=QDoubleSpinBox(); self.l_rate.setRange(0,100); self.l_rate.setDecimals(3); self.l_rate.setValue(15); self.l_days=QSpinBox(); self.l_days.setRange(1,3650); self.l_days.setValue(100); self.l_charge=moneybox(); self.l_charge_name=QLineEdit("Processing Fee"); self.l_deduct=QComboBox(); self.l_deduct.addItems(["Deduct from disbursement","Collect separately"]); self.l_date=datebox(); self.l_mode=QComboBox(); self.l_mode.addItems(["Cash","UPI","Bank Transfer","Cheque","Other"]); self.l_ref=QLineEdit(); self.l_remarks=QLineEdit()
        for a,b in [("Customer *",self.l_customer),("Gross loan amount",self.l_gross),("Upfront interest rate (%)",self.l_rate),("Collection days",self.l_days),("Additional charge name",self.l_charge_name),("Additional charge amount",self.l_charge),("Charge treatment",self.l_deduct),("Start date",self.l_date),("Disbursement mode",self.l_mode),("Reference number",self.l_ref),("Remarks",self.l_remarks)]:form.addRow(a,b)
        self.calc_label=QLabel(); self.calc_label.setStyleSheet("background:#edf5fc;padding:12px;border-radius:7px;font-weight:600;color:#24476f;")
        for x in [self.l_gross,self.l_rate,self.l_days,self.l_charge]: x.valueChanged.connect(self.update_calculation)
        self.l_deduct.currentIndexChanged.connect(self.update_calculation); form.addRow("Calculation preview",self.calc_label)
        b=QPushButton("Create loan & record disbursement"); b.clicked.connect(lambda:self.safe(self.create_loan)); form.addRow(b); l.addWidget(box)
        self.lt=make_table(["Loan No.","Customer","Gross","Rate %","Days","Interest","Net Disbursed","Daily Target","Collected","Outstanding","Status"]); l.addWidget(self.lt,1); return w
    def update_calculation(self):
        gross=self.l_gross.value(); interest=round(gross*self.l_rate.value()/100,2); ch=self.l_charge.value(); deducted=self.l_deduct.currentIndex()==0; net=gross-interest-(ch if deducted else 0); daily=gross/max(1,self.l_days.value())
        self.calc_label.setText(f"Upfront interest: ₹{interest:,.2f}     |     Net disbursement: ₹{net:,.2f}     |     Collection target: ₹{gross:,.2f}     |     Daily collection: ₹{daily:,.2f}")
    def create_loan(self):
        if not self.l_customer.count(): raise RuntimeError("Create a customer first")
        mode=self.l_mode.currentText(); ref=self.l_ref.text().strip()
        if mode in ["UPI","Bank Transfer","Cheque"] and not ref: raise RuntimeError("Enter the UPI/bank/cheque reference")
        loan=req("POST","/loans",json={"customer_id":int(self.l_customer.currentData()),"gross_amount":self.l_gross.value(),"monthly_rate_pct":self.l_rate.value(),"collection_days":self.l_days.value(),"additional_charges":self.l_charge.value(),"charge_name":self.l_charge_name.text().strip() or None,"charge_deducted":self.l_deduct.currentIndex()==0,"start_date":self.l_date.date().toString("yyyy-MM-dd"),"mode":mode,"reference":ref or None,"remarks":self.l_remarks.text().strip() or None}).json()
        self.load_loans(); self.load_ledgers(); self.load_dashboard(); QMessageBox.information(self,"Loan created",f"Loan: {loan['loan_code']}\nGross: ₹{loan['gross_amount']:,.2f}\nUpfront interest: ₹{loan['upfront_interest']:,.2f}\nNet disbursement: ₹{loan['net_disbursement']:,.2f}\nCollection target: ₹{loan['total_target']:,.2f}\nDaily target: ₹{loan['total_target']/loan['collection_days']:,.2f}")
    def load_loans(self):
        loans=req("GET","/loans").json()
        if hasattr(self,'lt'): fill(self.lt,[dict(x,daily=x['total_target']/max(1,x['collection_days'])) for x in loans],["loan_code","customer_name","gross_amount","monthly_rate_pct","collection_days","upfront_interest","net_disbursement","daily","collected","outstanding","status"])
        if hasattr(self,'l_customer'):
            cur=self.l_customer.currentData(); self.l_customer.clear()
            for c in req("GET","/customers").json():self.l_customer.addItem(f"{c['customer_code']} — {c['name']}",c['id'])
            if cur is not None:
                ix=self.l_customer.findData(cur)
                if ix>=0:self.l_customer.setCurrentIndex(ix)
            self.update_calculation()

    def collection_page(self):
        w,l=page("Daily Collections","Record repayments against an individual loan sub-ledger")
        box=QFrame(); box.setObjectName("Card"); f=QFormLayout(box); f.setContentsMargins(18,18,18,18)
        self.p_loan=QComboBox(); self.p_date=datebox(); self.p_amount=moneybox(1000); self.p_mode=QComboBox(); self.p_mode.addItems(["Cash","UPI","Bank Transfer","Cheque","Other"]); self.p_ref=QLineEdit(); self.p_remarks=QLineEdit()
        for a,b in [("Loan sub-ledger",self.p_loan),("Collection date",self.p_date),("Amount received",self.p_amount),("Payment mode",self.p_mode),("Reference / cheque number",self.p_ref),("Remarks",self.p_remarks)]:f.addRow(a,b)
        btn=QPushButton("Record collection & generate receipt"); btn.clicked.connect(lambda:self.safe(self.record_payment)); f.addRow(btn); l.addWidget(box)
        self.pt=make_table(["Receipt No.","Loan No.","Customer","Date","Amount","Mode","Reference","Remarks"]); l.addWidget(self.pt,1); return w
    def record_payment(self):
        if not self.p_loan.count():raise RuntimeError("No loans available")
        mode=self.p_mode.currentText(); ref=self.p_ref.text().strip()
        if mode in ["UPI","Bank Transfer","Cheque"] and not ref:raise RuntimeError("Enter payment reference/cheque number")
        result=req("POST","/payments",json={"loan_id":int(self.p_loan.currentData()),"payment_date":self.p_date.date().toString("yyyy-MM-dd"),"amount":self.p_amount.value(),"mode":mode,"reference":ref or None,"remarks":self.p_remarks.text().strip() or None}).json()
        self.load_collections();self.load_loans();self.load_ledgers();self.load_dashboard();QMessageBox.information(self,"Receipt generated",f"Receipt: {result['receipt_code']}\nOutstanding: ₹{result['loan']['outstanding']:,.2f}\nStatus: {result['loan']['status']}")
    def load_collections(self):
        if hasattr(self,'pt'):
            self.p_loan.clear()
            for x in req("GET","/loans").json():
                if x['status']=="ACTIVE":self.p_loan.addItem(f"{x['loan_code']} — {x['customer_name']} — due ₹{x['outstanding']:,.2f}",x['id'])
            fill(self.pt,req("GET","/payments").json(),["receipt_code","loan_code","customer","date","amount","mode","reference","remarks"])

    def ledger_page(self):
        w,l=page("Investor & Company Ledgers","View investor capital, company funds and lending account balances")
        self.ledgert=make_table(["Account","Balance"]); l.addWidget(self.ledgert)
        self.ledgert.itemSelectionChanged.connect(self.show_ledger_entries)
        self.ledger_entries=make_table(["Transaction","Date","Direction","Amount","Mode","Reference","Remarks"]); l.addWidget(QLabel("Selected ledger transactions")); l.addWidget(self.ledger_entries,1)
        self.cap_inv=QComboBox(); self.cap_inv.addItems(ACCOUNTS[:3]); self.cap_amt=moneybox(300000); self.cap_date=datebox(); self.cap_mode=QComboBox(); self.cap_mode.addItems(["Bank Transfer","UPI","Cash","Cheque"]); self.cap_ref=QLineEdit(); self.cap_note=QLineEdit()
        box=QFrame();box.setObjectName("Card");f=QFormLayout(box);f.setContentsMargins(18,18,18,18)
        for a,b in [("Investor",self.cap_inv),("Contribution amount",self.cap_amt),("Date",self.cap_date),("Payment mode",self.cap_mode),("Reference",self.cap_ref),("Remarks",self.cap_note)]:f.addRow(a,b)
        btn=QPushButton("Record investor contribution to company");btn.clicked.connect(lambda:self.safe(self.record_capital));f.addRow(btn);l.addWidget(box);return w
    def record_capital(self):
        mode=self.cap_mode.currentText();ref=self.cap_ref.text().strip()
        if mode in ["UPI","Bank Transfer","Cheque"] and not ref:raise RuntimeError("Enter payment reference")
        req("POST","/capital-contributions",json={"investor_account":self.cap_inv.currentText(),"amount":self.cap_amt.value(),"entry_date":self.cap_date.date().toString("yyyy-MM-dd"),"mode":mode,"reference":ref or None,"remarks":self.cap_note.text().strip() or None})
        self.load_ledgers();self.load_dashboard();QMessageBox.information(self,"Recorded","Investor contribution and matching company entry recorded.")
    def load_ledgers(self):
        data=req("GET","/ledgers").json()
        if hasattr(self,'ledgert'):
            fill(self.ledgert,[{"account":x['account'],"balance":x['balance']} for x in data],["account","balance"])
        if hasattr(self,'trt'):
            fill(self.trt,[{"account":x['account'],"balance":x['balance']} for x in data],["account","balance"])
        if hasattr(self,'it'):
            interest=[x for x in data if x['account'] in ("Interest Ledger","Additional Charges Ledger")]
            fill(self.it,[{"account":x['account'],"balance":x['balance']} for x in interest],["account","balance"])
        self._ledger_cache=data
        self.show_ledger_entries()
        self.show_transfer_entries()
        self.show_interest_entries()
    def _selected_account(self, table_widget):
        items=table_widget.selectedItems()
        return items[0].text() if items else None
    def _fill_entries(self, target, account):
        if not hasattr(self,'_ledger_cache') or not hasattr(self,target): return
        found=next((x for x in self._ledger_cache if x['account']==account),None)
        rows=[] if not found else found['entries']
        fill(getattr(self,target),rows,["transaction_code","date","direction","amount","mode","reference","remarks"])
    def show_ledger_entries(self):
        if hasattr(self,'ledgert'): self._fill_entries('ledger_entries',self._selected_account(self.ledgert))
    def show_transfer_entries(self):
        if hasattr(self,'trt'): self._fill_entries('transfer_entries',self._selected_account(self.trt))
    def show_interest_entries(self):
        if hasattr(self,'it'): self._fill_entries('interest_entries',self._selected_account(self.it))

    def transfer_page(self):
        w,l=page("Fund Transfers","Move funds between investor, company, lending and interest accounts")
        box=QFrame();box.setObjectName("Card");f=QFormLayout(box);f.setContentsMargins(18,18,18,18)
        self.t_from=QComboBox();self.t_from.addItems(ACCOUNTS);self.t_to=QComboBox();self.t_to.addItems(ACCOUNTS);self.t_to.setCurrentText("Lending Account");self.t_amt=moneybox(1000);self.t_date=datebox();self.t_mode=QComboBox();self.t_mode.addItems(["Internal Transfer","Cash","UPI","Bank Transfer","Cheque","Other"]);self.t_ref=QLineEdit();self.t_note=QLineEdit()
        for a,b in [("From account",self.t_from),("To account",self.t_to),("Transfer amount",self.t_amt),("Transfer date",self.t_date),("Payment mode",self.t_mode),("Reference",self.t_ref),("Remarks",self.t_note)]:f.addRow(a,b)
        btn=QPushButton("Record linked fund transfer");btn.clicked.connect(lambda:self.safe(self.transfer));f.addRow(btn);l.addWidget(box)
        tip=QLabel("Each transfer creates an OUT entry in the source ledger and a matching IN entry in the destination ledger.");tip.setObjectName("Muted");l.addWidget(tip)
        self.trt=make_table(["Account","Balance"]);l.addWidget(self.trt); self.trt.itemSelectionChanged.connect(self.show_transfer_entries)
        self.transfer_entries=make_table(["Transaction","Date","Direction","Amount","Mode","Reference","Remarks"]); l.addWidget(QLabel("Selected account transactions")); l.addWidget(self.transfer_entries,1); return w
    def transfer(self):
        mode=self.t_mode.currentText();ref=self.t_ref.text().strip()
        if self.t_from.currentText()==self.t_to.currentText():raise RuntimeError("Choose different source and destination accounts")
        if mode in ["UPI","Bank Transfer","Cheque"] and not ref:raise RuntimeError("Enter payment reference")
        req("POST","/transfers",json={"amount":self.t_amt.value(),"from_account":self.t_from.currentText(),"to_account":self.t_to.currentText(),"entry_date":self.t_date.date().toString("yyyy-MM-dd"),"mode":mode,"reference":ref or None,"remarks":self.t_note.text().strip() or None})
        self.load_ledgers();self.load_dashboard();QMessageBox.information(self,"Transfer recorded","Both account ledgers have been updated.")

    def interest_page(self):
        w,l=page("Interest Ledger","Upfront interest is allocated when a loan is created; transfers are recorded separately")
        self.it=make_table(["Account","Balance"]);l.addWidget(self.it)
        self.it.itemSelectionChanged.connect(self.show_interest_entries)
        self.interest_entries=make_table(["Transaction","Date","Direction","Amount","Mode","Reference","Remarks"]); l.addWidget(self.interest_entries,1)
        info=QLabel("Interest allocation is an accounting entry, not a second cash receipt. Use Fund Transfers to move an available interest balance to Company Account or an Investor Ledger.");info.setWordWrap(True);info.setObjectName("Muted");l.addWidget(info);return w

    def report_page(self):
        w,l=page("Reports & Backup","Export the records or create a local database backup")
        box=QFrame();box.setObjectName("Card");v=QVBoxLayout(box);v.setContentsMargins(20,20,20,20)
        a=QLabel("Excel report includes loans, customers, collections and ledger transactions.");a.setObjectName("Muted");v.addWidget(a)
        b=QPushButton("Export Excel report");b.clicked.connect(lambda:self.safe(self.export_excel));v.addWidget(b)
        c=QPushButton("Create database backup");c.setObjectName("Secondary");c.clicked.connect(lambda:self.safe(self.backup));v.addWidget(c)
        l.addWidget(box);l.addStretch();return w
    def export_excel(self):
        r=req("GET","/reports/excel");path,_=QFileDialog.getSaveFileName(self,"Save Excel report","macha_finance_report.xlsx","Excel Workbook (*.xlsx)")
        if path:Path(path).write_bytes(r.content);QMessageBox.information(self,"Export complete",f"Saved: {path}")
    def backup(self):
        from backend import DB_PATH
        if not DB_PATH.exists():raise RuntimeError("Database file not found")
        path,_=QFileDialog.getSaveFileName(self,"Save database backup",f"macha_backup_{datetime.date.today()}.db","SQLite Database (*.db)")
        if path:shutil.copy2(DB_PATH,path);QMessageBox.information(self,"Backup complete",f"Saved: {path}")

def main():
    app=QApplication(sys.argv);app.setStyle("Fusion");win=Main();win.show();sys.exit(app.exec())
if __name__=="__main__":main()
