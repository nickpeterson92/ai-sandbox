# salesforce_tools.py


import os
from datetime import date

from pydantic import BaseModel
from langchain.tools import BaseTool
from typing import Optional
from simple_salesforce import Salesforce


def get_salesforce_connection():
    sf = Salesforce(
        username=os.environ["SFDC_USER"],
        password=os.environ["SFDC_PASS"],
        security_token=os.environ["SFDC_TOKEN"]
    )
    return sf


class GetLeadInput(BaseModel):
    lead_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None


class GetLeadTool(BaseTool):
    name: str = "get_lead_tool"
    description: str = (
        "Retrieves Salesforce leads by id. If no Id supplied, uses email, name, phone, or company. "
        "If multiple leads match, returns a list of options for user selection. "
        "Sometimes used in workflows involving tools that require a lead_id where one is not supplied."
    )
    args_schema: type = GetLeadInput
    
    def _run(self, **kwargs) -> dict:
        print(f"DEBUG: Tool 'get_lead_tool' invoked with input: {kwargs}")
        sf = get_salesforce_connection()
        data = GetLeadInput(**kwargs)
        
        lead_id = data.lead_id
        email = data.email
        name = data.name
        phone = data.phone
        company = data.company

        if lead_id:
            query =f"SELECT Id, Name, Company, Email, Phone FROM Lead WHERE Id = '{lead_id}'"
        else:
            query_conditions = []
            if email:
                query_conditions.append(f"Email LIKE '%{email}%'")
            if name:
                query_conditions.append(f"Name LIKE '%{name}%'")
            if phone:
                query_conditions.append(f"Phone LIKE '%{phone}%'")
            if company:
                query_conditions.append(f"Company LIKE '%{company}%'")
    
            query = f"SELECT Id, Name, Company, Email, Phone FROM Lead WHERE {' AND '.join(query_conditions)}"
            print(f"DEBUG: Executing SOQL query: {query}")

        result = sf.query(query)
        records = result.get("records", [])

        if not records:
            return {"error": "No leads found."}

        if len(records) > 1:
            return {
                "multiple_matches": [
                    {
                        "id": rec["Id"],
                        "name": rec["Name"],
                        "company": rec["Company"],
                        "email": rec["Email"],
                        "phone": rec["Phone"]
                    }
                    for rec in records
                ]
            }

        return {
            "match": records[0]
        }
    

class CreateLeadInput(BaseModel):
    name: str
    company: str
    email: str
    phone: str


class CreateLeadTool(BaseTool):
    name: str = "create_lead_tool"
    description: str = (
        "Creates a new Salesforce lead. Requires: name, company, email, and phone."
    )
    args_schema: type = CreateLeadInput

    def _run(self, **kwargs) -> dict:
        sf = get_salesforce_connection()
        data = CreateLeadInput(**kwargs)
        result = sf.Lead.create({
            "LastName": data.name,
            "Company": data.company,
            "Email": data.email,
            "Phone": data.phone
        })
        return {"message": f"Lead created with ID: {result['id']}"}
    

class UpdateLeadInput(BaseModel):
    lead_id: str
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class UpdateLeadTool(BaseTool):
    name: str = "update_lead_tool"
    description: str = (
        "Updates an existing Salesforce lead. Requires a lead_id. "
        "Optionally takes a company, email, and/or phone."
    )
    args_schema: type = UpdateLeadInput

    def _run(self, **kwargs) -> dict:
        sf = get_salesforce_connection()
        data = UpdateLeadInput(**kwargs)
        result = sf.Lead.update(data.lead_id, {
            "Company": data.company,
            "Email": data.email,
            "Phone": data.phone
        })
        return {"message": f"Lead updated with ID: {result['id']}"}
    

class GetOpportunityInput(BaseModel):
    opportunity_id: Optional[str] = None
    account_name: Optional[str] = None
    opportunity_name: Optional[str] = None


class GetOpportunityTool(BaseTool):
    name: str = "get_opportunity_tool"
    description: str = (
        "Retrieves Salesforce opportunities, always by opportunity_id if one is available. "
        "If no opportunity_id available, uses account_name, opportunity_name, or both. "
        "If multiple opportunities match, returns a list of options for user selection. "
        "Sometimes used in workflows involving tools that require an opportunity_id where one is not supplied."
    )
    args_schema: type = GetOpportunityInput
    
    def _run(self, **kwargs) -> dict:
        print(f"DEBUG: Tool 'get_opportunity_tool' invoked with input: {kwargs}")
        sf = get_salesforce_connection()
        data = GetOpportunityInput(**kwargs)
        
        account_name = data.account_name
        opportunity_name = data.opportunity_name
        opportunity_id = data.opportunity_id

        if opportunity_id:
            query =f"SELECT Id, Name, StageName, Amount, Account.Name FROM Opportunity WHERE Id = '{opportunity_id}'"
        else:
            query_conditions = [f"Account.Name LIKE '%{account_name}%'"]
            if opportunity_name:
                query_conditions.append(f"Name LIKE '%{opportunity_name}%'")
    
            query = f"SELECT Id, Name, StageName, Amount, Account.Name FROM Opportunity WHERE {' AND '.join(query_conditions)}"
            print(f"DEBUG: Executing SOQL query: {query}")

        result = sf.query(query)
        records = result.get("records", [])

        if not records:
            return {"error": "No opportunities found."}

        if len(records) > 1:
            return {
                "multiple_matches": [
                    {
                        "id": rec["Id"],
                        "name": rec["Name"],
                        "account": rec["Account"]["Name"],
                        "stage": rec["StageName"],
                        "amount": rec["Amount"],
                    }
                    for rec in records
                ]
            }

        return {
            "match": records[0]
        }
    

class CreateOpportunityInput(BaseModel):
    opportunity_name: str
    account_id: str
    stage_name: Optional[str] = "New"
    close_date: Optional[str] = str(date.today())
    amount: float


class CreateOpportunityTool(BaseTool):
    name: str = "create_opportunity_tool"
    description: str = (
        "Creates an opportunity. Requires an opportunity_name, an amount, a stage_name, "
        "a close_date, and the Salesforce Id of the account the opportunity is for."
    )
    args_schema: type = CreateOpportunityInput

    def _run(self, **kwargs) -> dict:
        print(f"DEBUG: Tool 'create_opportunity_tool' invoked with input: {kwargs}")
        sf = get_salesforce_connection()

        data = CreateOpportunityInput(**kwargs)

        opportunity_name = data.opportunity_name
        amount = data.amount
        account_id = data.account_id
        stage_name = data.stage_name
        close_date = data.close_date

        try:
            sf.Opportunity.create({
                "Name": opportunity_name,
                "AccountId": account_id,
                "Amount": amount,
                "StageName": stage_name,
                "CloseDate": close_date
            })
        except Exception as e:
            return {"error": str(e)}
        

class UpdateOpportunityInput(BaseModel):
    opportunity_id: str
    stage: str
    amount: Optional[float] = None


class UpdateOpportunityTool(BaseTool):
    name: str = "update_opportunity_tool"
    description: str = (
        "Updates an existing Opportunity. Called directly if an opportunity_id is provided. "
        "If opportunity_id not provided, the get_opportunity_tool is called to retrieve the opportunity_id."
    )
    args_schema: type = UpdateOpportunityInput

    def _run(self, **kwargs) -> dict:
        print(f"DEBUG: Tool 'update_opportunity_tool' invoked with input: {kwargs}")
        sf = get_salesforce_connection()

        data = UpdateOpportunityInput(**kwargs)

        stage = data.stage
        amount = data.amount
        opp_id = data.opportunity_id
        
        try:
            sf.Opportunity.update(opp_id, {
                "StageName": stage,
                "Amount": amount
            })
            return {
                "message": f"Opportunity updated successfully with ID: {opp_id}",
                "stage": stage,
                "amount": amount
            }
        except Exception as e:
            return {"error": str(e)}


class GetAccountInput(BaseModel):
    account_id: Optional[str] = None
    account_name: Optional[str] = None


class GetAccountTool(BaseTool):
    name: str = "get_account_tool"
    description: str = (
        "Retrieves Salesforce accounts by id. If no Id supplied, uses account_name. "
        "If multiple accounts match, returns a list of options for user selection. "
        "Sometimes used in workflows involving tools that require an account_id where one is not supplied."
    )
    args_schema: type = GetAccountInput
    
    def _run(self, **kwargs) -> dict:
        print(f"DEBUG: Tool 'get_account_tool' invoked with input: {kwargs}")
        sf = get_salesforce_connection()
        data = GetAccountInput(**kwargs)
        
        account_id = data.account_id
        account_name = data.account_name

        if account_id:
            query =f"SELECT Id, Name FROM Account WHERE Id = '{account_id}'"
        else:
            query_conditions = [f"Account.Name LIKE '%{account_name}%'"]
    
            query = f"SELECT Id, Name FROM Account WHERE {' AND '.join(query_conditions)}"
            print(f"DEBUG: Executing SOQL query: {query}")

        result = sf.query(query)
        records = result.get("records", [])

        if not records:
            return {"error": "No accounts found."}

        if len(records) > 1:
            return {
                "multiple_matches": [
                    {
                        "id": rec["Id"],
                        "name": rec["Name"],
                        "account": rec["Account"]["Name"],
                        "stage": rec["StageName"],
                        "amount": rec["Amount"],
                    }
                    for rec in records
                ]
            }

        return {
            "match": records[0]
        }
    

class CreateAccountInput(BaseModel):
    account_name: str
    phone: str
    website: Optional[str] = None


class CreateAccountTool(BaseTool):
    name: str = "create_account_tool"
    description: str = (
        "Creates a new Salesforce account. Requires: account_name and phone. "
        "Optionally takes a website."
    )
    args_schema: type = CreateAccountInput

    def _run(self, **kwargs) -> dict:
        print(f"DEBUG: Tool 'create_account_tool' invoked with input: {kwargs}")
        sf = get_salesforce_connection()
        data = CreateAccountInput(**kwargs)
        result = sf.Account.create({
            "Name": data.account_name,
            "Phone": data.phone,
            "Website": data.website
        })
        return {"message": f"Account created with ID: {result['id']}"}


class UpdateAccountInput(BaseModel):
    account_id: str
    phone: Optional[str] = None
    website: Optional[str] = None


class UpdateAccountTool(BaseTool):
    name: str = "update_account_tool"
    description: str = (
        "Updates an existing Salesforce account. Requires an account_id. "
        "Optionally takes a phone and/or website."
    )
    args_schema: type = UpdateAccountInput

    def _run(self, **kwargs) -> dict:
        print(f"DEBUG: Tool 'update_account_tool' invoked with input: {kwargs}")
        sf = get_salesforce_connection()
        data = UpdateAccountInput(**kwargs)
        result = sf.Account.update(data.account_id, {
            "Phone": data.phone,
            "Website": data.website
        })
        return {"message": f"Account updated with ID: {data.account_id}"}