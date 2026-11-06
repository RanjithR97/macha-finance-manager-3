from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import os
import sys
import secrets
import string

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

# Keep persistent user data outside the PyInstaller temporary extraction directory.
if getattr(sys, "frozen", False):
    _appdata = Path(os.environ.get("APPDATA", str(Path.home())))
    ROOT = _appdata / "MachaFinanceManager"
    ROOT.mkdir(parents=True, exist_ok=True)
else:
    ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "macha_finance.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    customer_code = Column(String(30), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    dob = Column(Date, nullable=True)
    aadhaar_encrypted = Column(String(500), nullable=True)
    pan = Column(String(20), nullable=True)
    phone = Column(String(30), nullable=True)
    security_doc_name = Column(String(200), nullable=True)
    security_doc_number = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    loans = relationship("Loan", back_populates="customer")

class Loan(Base):
    __tablename__ = "loans"
    id = Column(Integer, primary_key=True)
    loan_code = Column(String(30), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    gross_amount = Column(Numeric(14,2), nullable=False)
    monthly_rate_pct = Column(Numeric(7,3), nullable=False)
    collection_days = Column(Integer, nullable=False)
    upfront_interest = Column(Numeric(14,2), nullable=False)
    additional_charges = Column(Numeric(14,2), nullable=False, default=0)
    charge_name = Column(String(200), nullable=True)
    charge_deducted = Column(Boolean, default=True)
    net_disbursement = Column(Numeric(14,2), nullable=False)
    total_target = Column(Numeric(14,2), nullable=False)
    start_date = Column(Date, nullable=False)
    status = Column(String(20), default="ACTIVE")
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    customer = relationship("Customer", back_populates="loans")
    payments = relationship("Payment", back_populates="loan")

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id = Column(Integer, primary_key=True)
    transaction_code = Column(String(40), unique=True, nullable=False)
    entry_date = Column(Date, nullable=False)
    account = Column(String(100), nullable=False)
    direction = Column(String(10), nullable=False) # IN or OUT
    amount = Column(Numeric(14,2), nullable=False)
    mode = Column(String(30), nullable=False)
    reference = Column(String(200), nullable=True)
    remarks = Column(Text, nullable=True)
    related_type = Column(String(40), nullable=True)
    related_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    receipt_code = Column(String(40), unique=True, nullable=False)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False)
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(14,2), nullable=False)
    mode = Column(String(30), nullable=False)
    reference = Column(String(200), nullable=True)
    remarks = Column(Text, nullable=True)
    loan = relationship("Loan", back_populates="payments")

Base.metadata.create_all(engine)
app = FastAPI(title="Macha Finance Manager API", version="0.2.0")

class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    dob: date | None = None
    aadhaar: str | None = None
    pan: str | None = None
    phone: str | None = None
    security_doc_name: str | None = None
    security_doc_number: str | None = None

class LoanIn(BaseModel):
    customer_id: int
    gross_amount: Decimal = Field(gt=0)
    monthly_rate_pct: Decimal = Field(ge=0, le=100)
    collection_days: int = Field(gt=0, le=3650)
    additional_charges: Decimal = Field(default=Decimal("0"), ge=0)
    charge_name: str | None = None
    charge_deducted: bool = True
    start_date: date = Field(default_factory=date.today)
    mode: str = "Bank Transfer"
    reference: str | None = None
    remarks: str | None = None

class PaymentIn(BaseModel):
    loan_id: int
    payment_date: date = Field(default_factory=date.today)
    amount: Decimal = Field(gt=0)
    mode: str = "Cash"
    reference: str | None = None
    remarks: str | None = None

class TransferIn(BaseModel):
    amount: Decimal = Field(gt=0)
    from_account: str
    to_account: str
    entry_date: date = Field(default_factory=date.today)
    mode: str = "Bank Transfer"
    reference: str | None = None
    remarks: str | None = None

class CapitalContributionIn(BaseModel):
    investor_account: str
    amount: Decimal = Field(gt=0)
    entry_date: date = Field(default_factory=date.today)
    mode: str = "Bank Transfer"
    reference: str | None = None
    remarks: str | None = None

class ManualEntryIn(BaseModel):
    account: str
    direction: str
    amount: Decimal = Field(gt=0)
    entry_date: date = Field(default_factory=date.today)
    mode: str = "Cash"
    reference: str | None = None
    remarks: str | None = None


def money(x):
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def code(prefix, n):
    return f"{prefix}-{date.today().year}-{n:06d}"

def next_code(db, model, prefix, attr):
    n = db.query(model).count() + 1
    candidate = code(prefix, n)
    while db.query(model).filter(getattr(model, attr) == candidate).first():
        n += 1
        candidate = code(prefix, n)
    return candidate

def add_entry(db, account, direction, amount, mode, reference, remarks, related_type=None, related_id=None, entry_date=None):
    entry = LedgerEntry(transaction_code=next_code(db, LedgerEntry, "TXN", "transaction_code"), entry_date=entry_date or date.today(), account=account, direction=direction, amount=money(amount), mode=mode, reference=reference, remarks=remarks, related_type=related_type, related_id=related_id)
    db.add(entry)
    return entry

def customer_dict(c):
    return {"id":c.id,"customer_code":c.customer_code,"name":c.name,"dob":str(c.dob) if c.dob else "","pan":c.pan or "","phone":c.phone or "","security_doc_name":c.security_doc_name or "","security_doc_number":c.security_doc_number or "","aadhaar_masked":("XXXX-XXXX-"+c.aadhaar_encrypted[-4:]) if c.aadhaar_encrypted else ""}

def loan_dict(db, l):
    collected = sum((money(p.amount) for p in l.payments), Decimal("0.00"))
    return {"id":l.id,"loan_code":l.loan_code,"customer_id":l.customer_id,"customer_name":l.customer.name,"gross_amount":float(l.gross_amount),"monthly_rate_pct":float(l.monthly_rate_pct),"collection_days":l.collection_days,"upfront_interest":float(l.upfront_interest),"additional_charges":float(l.additional_charges),"charge_name":l.charge_name or "","charge_deducted":bool(l.charge_deducted),"net_disbursement":float(l.net_disbursement),"total_target":float(l.total_target),"collected":float(collected),"outstanding":float(max(Decimal("0"), money(l.total_target)-collected)),"start_date":str(l.start_date),"status":l.status,"remarks":l.remarks or ""}

def ledger_balance(db, account):
    entries = db.query(LedgerEntry).filter(LedgerEntry.account == account).all()
    return float(sum((money(e.amount) if e.direction == "IN" else -money(e.amount) for e in entries), Decimal("0.00")))

@app.get("/health")
def health():
    return {"status":"ok","app":"Macha Finance Manager","version":"0.2.0"}

@app.get("/customers")
def list_customers():
    with SessionLocal() as db:
        return [customer_dict(c) for c in db.query(Customer).order_by(Customer.id.desc()).all()]

@app.post("/customers")
def create_customer(data: CustomerIn):
    with SessionLocal() as db:
        n = db.query(Customer).count() + 1
        customer = Customer(customer_code=code("CUST", n), name=data.name.strip(), dob=data.dob, aadhaar_encrypted=data.aadhaar, pan=(data.pan or "").upper() or None, phone=data.phone, security_doc_name=data.security_doc_name, security_doc_number=data.security_doc_number)
        db.add(customer); db.commit(); db.refresh(customer)
        return customer_dict(customer)

@app.get("/loans")
def list_loans():
    with SessionLocal() as db:
        return [loan_dict(db,l) for l in db.query(Loan).order_by(Loan.id.desc()).all()]

@app.post("/loans")
def create_loan(data: LoanIn):
    with SessionLocal() as db:
        customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
        if not customer: raise HTTPException(404, "Customer not found")
        if data.mode.lower() in {"upi","bank transfer","neft","imps","rtgs","online"} and not (data.reference or "").strip():
            raise HTTPException(400, "Reference number is required for online/bank payments")
        gross = money(data.gross_amount)
        interest = money(gross * data.monthly_rate_pct / Decimal("100"))
        charges = money(data.additional_charges)
        net = money(gross - interest - (charges if data.charge_deducted else Decimal("0")))
        if net < 0: raise HTTPException(400, "Interest and deducted charges cannot exceed gross loan amount")
        n = db.query(Loan).count() + 1
        loan = Loan(loan_code=code("LN",n), customer_id=customer.id, gross_amount=gross, monthly_rate_pct=data.monthly_rate_pct, collection_days=data.collection_days, upfront_interest=interest, additional_charges=charges, charge_name=data.charge_name, charge_deducted=data.charge_deducted, net_disbursement=net, total_target=gross, start_date=data.start_date, status="ACTIVE", remarks=data.remarks)
        db.add(loan); db.flush()
        # Actual fund movement: only net amount leaves the Lending Account.
        add_entry(db,"Lending Account","OUT",net,data.mode,data.reference,f"Loan disbursement {loan.loan_code}; {data.remarks or ''}","loan",loan.id,data.start_date)
        # Interest allocation is an accounting record, not a cash receipt.
        if interest > 0:
            add_entry(db,"Interest Ledger","IN",interest,"Internal Allocation",None,f"Upfront interest allocation for {loan.loan_code}","loan",loan.id,data.start_date)
        if charges > 0:
            add_entry(db,"Additional Charges Ledger","IN",charges,"Internal Allocation",None,f"{data.charge_name or 'Additional charge'} for {loan.loan_code}; deducted={data.charge_deducted}","loan",loan.id,data.start_date)
        db.commit(); db.refresh(loan)
        return loan_dict(db,loan)

@app.post("/payments")
def create_payment(data: PaymentIn):
    with SessionLocal() as db:
        loan = db.query(Loan).filter(Loan.id == data.loan_id).first()
        if not loan: raise HTTPException(404,"Loan not found")
        if loan.status == "CLOSED": raise HTTPException(400,"Loan is already closed")
        if data.mode.lower() in {"upi","bank transfer","neft","imps","rtgs","online"} and not (data.reference or "").strip():
            raise HTTPException(400,"Reference number is required for online/bank payments")
        collected = sum((money(p.amount) for p in loan.payments), Decimal("0.00"))
        outstanding = money(loan.total_target) - collected
        if money(data.amount) > outstanding: raise HTTPException(400,f"Payment exceeds outstanding balance of ₹{outstanding}")
        receipt = next_code(db,Payment,"RCT","receipt_code")
        payment = Payment(receipt_code=receipt, loan_id=loan.id, payment_date=data.payment_date, amount=money(data.amount), mode=data.mode, reference=data.reference, remarks=data.remarks)
        db.add(payment); db.flush()
        # Collections are routed to Lending Account, per the agreed model.
        add_entry(db,"Lending Account","IN",data.amount,data.mode,data.reference,f"Collection {receipt} for {loan.loan_code}; {data.remarks or ''}","payment",payment.id,data.payment_date)
        new_collected = collected + money(data.amount)
        if new_collected >= money(loan.total_target): loan.status = "CLOSED"
        db.commit(); db.refresh(payment); db.refresh(loan)
        return {"receipt_code":receipt,"loan":loan_dict(db,loan),"lending_account_balance":ledger_balance(db,"Lending Account")}

@app.get("/ledgers")
def ledgers():
    accounts = ["Investor 1 Ledger","Investor 2 Ledger","Investor 3 Ledger","Company Account","Lending Account","Interest Ledger","Additional Charges Ledger","Company Cash Ledger","Company Bank Ledger"]
    with SessionLocal() as db:
        result=[]
        for account in accounts:
            entries=db.query(LedgerEntry).filter(LedgerEntry.account==account).order_by(LedgerEntry.id.desc()).all()
            result.append({"account":account,"balance":ledger_balance(db,account),"entries":[{"transaction_code":e.transaction_code,"date":str(e.entry_date),"direction":e.direction,"amount":float(e.amount),"mode":e.mode,"reference":e.reference or "","remarks":e.remarks or ""} for e in entries]})
        return result

@app.get("/payments")
def list_payments():
    with SessionLocal() as db:
        result=[]
        for p in db.query(Payment).order_by(Payment.id.desc()).all():
            result.append({"receipt_code":p.receipt_code,"loan_code":p.loan.loan_code,"customer":p.loan.customer.name,"date":str(p.payment_date),"amount":float(p.amount),"mode":p.mode,"reference":p.reference or "","remarks":p.remarks or ""})
        return result

@app.post("/capital-contributions")
def capital_contribution(data: CapitalContributionIn):
    allowed={"Investor 1 Ledger","Investor 2 Ledger","Investor 3 Ledger"}
    if data.investor_account not in allowed: raise HTTPException(400,"Select a valid investor ledger")
    if data.mode.lower() in {"upi","bank transfer","neft","imps","rtgs","online"} and not (data.reference or "").strip(): raise HTTPException(400,"Reference number is required for online/bank contributions")
    with SessionLocal() as db:
        # Capital is first recorded in the investor's source ledger.
        # It reaches the Company Account only when the user records an explicit transfer.
        add_entry(db,data.investor_account,"IN",data.amount,data.mode,data.reference,f"Investor capital received and available for transfer; {data.remarks or ''}","capital_contribution",None,data.entry_date)
        db.commit()
        return {"status":"recorded","investor_account":data.investor_account,"investor_balance":ledger_balance(db,data.investor_account),"company_balance":ledger_balance(db,"Company Account")}

@app.post("/transfers")
def transfer(data: TransferIn):
    if data.from_account.strip() == data.to_account.strip(): raise HTTPException(400,"Source and destination accounts must differ")
    if data.mode.lower() in {"upi","bank transfer","neft","imps","rtgs","online"} and not (data.reference or "").strip(): raise HTTPException(400,"Reference number is required for online/bank transfers")
    with SessionLocal() as db:
        source_balance = ledger_balance(db,data.from_account)
        if money(data.amount) > money(source_balance): raise HTTPException(400,f"Insufficient recorded balance in {data.from_account}: ₹{money(source_balance)}")
        add_entry(db,data.from_account,"OUT",data.amount,data.mode,data.reference,f"Transfer to {data.to_account}; {data.remarks or ''}","transfer",None,data.entry_date)
        add_entry(db,data.to_account,"IN",data.amount,data.mode,data.reference,f"Transfer from {data.from_account}; {data.remarks or ''}","transfer",None,data.entry_date)
        db.commit()
        return {"status":"recorded","from_account":data.from_account,"from_balance":ledger_balance(db,data.from_account),"to_account":data.to_account,"to_balance":ledger_balance(db,data.to_account)}

@app.post("/ledger-entries")
def manual_entry(data: ManualEntryIn):
    direction=data.direction.upper()
    if direction not in {"IN","OUT"}: raise HTTPException(400,"Direction must be IN or OUT")
    if data.mode.lower() in {"upi","bank transfer","neft","imps","rtgs","online"} and not (data.reference or "").strip(): raise HTTPException(400,"Reference number is required for online/bank entries")
    with SessionLocal() as db:
        if direction == "OUT" and money(data.amount) > money(ledger_balance(db,data.account)):
            raise HTTPException(400,"Insufficient recorded account balance")
        e=add_entry(db,data.account,direction,data.amount,data.mode,data.reference,data.remarks,entry_date=data.entry_date)
        db.commit(); db.refresh(e)
        return {"transaction_code":e.transaction_code,"balance":ledger_balance(db,data.account)}

@app.get("/reports/excel")
def export_excel():
    with SessionLocal() as db:
        wb=Workbook()
        ws=wb.active; ws.title="Loans"
        headers=["Loan Number","Customer ID","Customer Name","Gross Amount","Interest Rate %/month","Collection Days","Upfront Interest","Additional Charges","Charge Name","Net Disbursement","Collection Target","Collected","Outstanding","Start Date","Status","Remarks"]
        ws.append(headers)
        for l in db.query(Loan).order_by(Loan.id).all():
            d=loan_dict(db,l); ws.append([d["loan_code"],d["customer_id"],d["customer_name"],d["gross_amount"],d["monthly_rate_pct"],d["collection_days"],d["upfront_interest"],d["additional_charges"],d["charge_name"],d["net_disbursement"],d["total_target"],d["collected"],d["outstanding"],d["start_date"],d["status"],d["remarks"]])
        wc=wb.create_sheet("Customers"); wc.append(["Customer ID","Name","DOB","PAN","Phone","Security Doc Name","Security Doc Number","Aadhaar (masked)"])
        for c in db.query(Customer).order_by(Customer.id).all():
            d=customer_dict(c); wc.append([d["customer_code"],d["name"],d["dob"],d["pan"],d["phone"],d["security_doc_name"],d["security_doc_number"],d["aadhaar_masked"]])
        wp=wb.create_sheet("Collections"); wp.append(["Receipt Number","Loan Number","Customer","Date","Amount","Mode","Reference","Remarks"])
        for p in db.query(Payment).order_by(Payment.id).all(): wp.append([p.receipt_code,p.loan.loan_code,p.loan.customer.name,str(p.payment_date),float(p.amount),p.mode,p.reference or "",p.remarks or ""])
        wl=wb.create_sheet("Ledger Entries"); wl.append(["Transaction Number","Date","Account","Direction","Amount","Mode","Reference","Remarks"])
        for e in db.query(LedgerEntry).order_by(LedgerEntry.id).all(): wl.append([e.transaction_code,str(e.entry_date),e.account,e.direction,float(e.amount),e.mode,e.reference or "",e.remarks or ""])
        for sheet in wb.worksheets:
            sheet.freeze_panes="A2"; sheet.auto_filter.ref=sheet.dimensions
            for cell in sheet[1]: cell.font=Font(bold=True,color="FFFFFF"); cell.fill=PatternFill("solid",fgColor="1F4E78")
            for col in sheet.columns:
                letter=col[0].column_letter
                max_len=max((len(str(cell.value or "")) for cell in col[:200]),default=10)
                sheet.column_dimensions[letter].width=min(max(max_len+2,12),32)
        path=ROOT/"macha_finance_report.xlsx"; wb.save(path)
        return FileResponse(path,filename="macha_finance_report.xlsx",media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.get("/dashboard")
def dashboard():
    with SessionLocal() as db:
        loans=db.query(Loan).all(); customers=db.query(Customer).count()
        total_target=sum((money(l.total_target) for l in loans),Decimal("0"))
        total_collected=sum((sum((money(p.amount) for p in l.payments),Decimal("0")) for l in loans),Decimal("0"))
        return {"customers":customers,"loans":len(loans),"active_loans":sum(1 for l in loans if l.status=="ACTIVE"),"closed_loans":sum(1 for l in loans if l.status=="CLOSED"),"total_target":float(total_target),"total_collected":float(total_collected),"outstanding":float(max(Decimal("0"),total_target-total_collected)),"lending_balance":ledger_balance(db,"Lending Account"),"interest_ledger_balance":ledger_balance(db,"Interest Ledger")}
