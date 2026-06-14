# graphdb_operations.py
# Script for controlling the gantry robot of the digital twin testbed described in:
# Čustović, I. et al. (2026). Experimenting with Digital Twins: a LEGO®-based Modular Testbed for Systematic Evaluation. EC3 Conference 2026. Corfu, Greece. Available at: https://doi.org/10.35490/EC3.2026.233.
#
# Copyright (c) 2026 Irfan Čustović, Emilio Murillo Sierra, Ranjith K. Soman, Daniel M. Hall | TU Delft
# Licensed under the MIT License.
# See the 'licenses/' folder in the repository root for details.


import os
import requests
from fastapi import HTTPException

from typing import Dict, Any
import random

sparqlPrefix = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX aic: <https://www.w3id.org/aic#>
    PREFIX ex:  <http://example.org/aic-example#>
"""

# For SPARQL "select" queries
GRAPHDB_BASE_URL = os.getenv("GRAPHDB_URL", "http://graphdb:7200").rstrip("/")
GRAPHDB_REPOSITORY = os.getenv("GRAPHDB_REPOSITORY", "prodRepo").strip("/")

if not GRAPHDB_REPOSITORY:
    raise RuntimeError("GRAPHDB_REPOSITORY must not be empty.")

# For SPARQL SELECT queries
GRAPHDB_ENDPOINT = f"{GRAPHDB_BASE_URL}/repositories/{GRAPHDB_REPOSITORY}"

# For SPARQL UPDATE statements
GRAPHDB_ENDPOINT_STATEMENTS = f"{GRAPHDB_ENDPOINT}/statements"

# For repository size checks
GRAPHDB_ENDPOINT_SIZE = f"{GRAPHDB_ENDPOINT}/size"

from .config_agent import thisAgentID

# # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# # GENERIC FUNCTIONS
# # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

AIC_PREFIX = "aic:"
EX_PREFIX = "ex:"

def _is_prefixed_iri(value: str) -> bool:
    return value.startswith((AIC_PREFIX, EX_PREFIX))

def _iri(value: str, default_prefix: str) -> str:
    """
    Convert a local name into a prefixed IRI.

    Examples:
    - _iri("Idle", "ex:") -> "ex:Idle"
    - _iri("ex:Idle", "ex:") -> "ex:Idle"
    - _iri("", "ex:") -> ""
    """
    if not value:
        return ""

    if _is_prefixed_iri(value):
        return value

    return f"{default_prefix}{value}"

def _aic(value: str) -> str:
    """Use for AiC ontology terms: classes, properties, information types."""
    return _iri(value, AIC_PREFIX)

def _ex(value: str) -> str:
    """Use for domain/example instances."""
    return _iri(value, EX_PREFIX)

async def getRepositorySize ():
    
    headers = {
        "Content-Type": "text/plain",
    }
    response = requests.get(url=GRAPHDB_ENDPOINT_SIZE, headers=headers)
    if response.status_code != 200:
         raise HTTPException(status_code=response.status_code, detail=response.text)
    
    size = int(response.text)

    return size

async def graphDBupdateStatements(
    subject : str,
    predicate : str,
    object : str,
    informationType : str,
    point_in_time : str,
    queryType : str,
    objectClass=""
):
    
    sizeBefore = await getRepositorySize()
    
    subject_iri = _ex(subject)
    predicate_iri = _aic(predicate)
    object_iri = _ex(object)
    objectClass_iri = _aic(objectClass)
    informationType_iri = _aic(informationType)
    
    sparql_query = get_sparql_query(queryType, subject_iri, predicate_iri, object_iri, informationType_iri, point_in_time, objectClass_iri)
    
    headers = {
        "Content-Type": "application/sparql-update",
    }

    response = requests.post(url=GRAPHDB_ENDPOINT_STATEMENTS, data=sparql_query, headers=headers)
    if response.status_code != 204:
         raise HTTPException(status_code=response.status_code, detail=response.text)
    
    sizeAfter = await getRepositorySize()
    sizeDifference = sizeAfter - sizeBefore
    
    return sizeDifference

async def graphDBgetValidStatements(
    subject : str,
    predicate : str,
    object : str,
    informationType : str,
    point_in_time : str,
    queryType : str,
    objectClass=""
) -> Dict[str, Any]:
    
    subject_iri = _ex(subject)
    predicate_iri = _aic(predicate)
    object_iri = _ex(object)
    objectClass_iri = _aic(objectClass)
    informationType_iri = _aic(informationType)
        
    sparql_query = get_sparql_query(queryType, subject_iri, predicate_iri, object_iri, informationType_iri, point_in_time, objectClass_iri)
    
    headers = {
        "Content-Type": "application/sparql-query",
        "Accept": "application/sparql-results+json"
    } 

    response = requests.post(url=GRAPHDB_ENDPOINT, data=sparql_query, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    bindings = response.json().get("results", {}).get("bindings", [])

    return bindings

def generateInformationID() -> str:
    
    number1 = random.randint(1000, 9999)
    number2 = random.randint(1000, 9999)
    return f"infoID-{number1}-{number2}"


def get_sparql_query(
    queryType: str,
    subject_iri: str,
    predicate_iri: str,
    object_iri: str,
    informationType_iri: str,
    point_in_time: str,
    objectClass_iri: str = "",
):
    
    sparql_query = ""
    objectClassStringInsert = ""
    objectClassStringSelect = ""
    object_bind_string = ""
    informationTypeString = ""
    subject_bind_string = ""

    generated_by_iri = _ex(thisAgentID)
    
    if subject_iri:
        subject_bind_string = f"BIND({subject_iri} AS ?subject) ."
        
    if object_iri:
        object_bind_string = f"BIND({object_iri} AS ?object) ."
               
    if objectClass_iri:
        if object_iri:
            objectClassStringInsert = f"{object_iri} a {objectClass_iri} ."

        objectClassStringSelect = f"?object a {objectClass_iri} ."

    if informationType_iri:
        informationTypeString = f""";
                aic:hasInformationType {informationType_iri} """
        
              
        
    if queryType == "application-startup":
        
        temp_informationID_1 = _ex(generateInformationID())
        temp_informationID_2 = _ex(generateInformationID())
        
        sparql_query = sparqlPrefix + f"""
        INSERT {{
            ex:Idle a aic:OperationMode .
            ex:Idle aic:hasModeMetric ex:GantryRobotIdleModeConsumption .
            ex:GantryRobotIdleModeConsumption aic:hasValue "3.52"^^xsd:decimal .
            ex:GantryRobotIdleModeConsumption aic:hasUnit "W"^^xsd:string .
            
            ex:PickingUp a aic:OperationMode .
            ex:PickingUp aic:hasModeMetric ex:GantryRobotPickingUpModeMetric .
            ex:GantryRobotPickingUpModeMetric aic:hasValue "12.96"^^xsd:decimal .
            ex:GantryRobotPickingUpModeMetric aic:hasUnit "W"^^xsd:string .
            
            ex:DroppingOff a aic:OperationMode .
            ex:DroppingOff aic:hasModeMetric ex:GantryRobotDroppingOffModeMetric .
            ex:GantryRobotDroppingOffModeMetric aic:hasValue "12.96"^^xsd:decimal .
            ex:GantryRobotDroppingOffModeMetric aic:hasUnit "W"^^xsd:string .
            
            ex:Calibrating a aic:OperationMode .
            ex:Calibrating aic:hasModeMetric ex:GantryRobotCalibratingModeMetric .
            ex:GantryRobotCalibratingModeMetric aic:hasValue "17.04"^^xsd:decimal .
            ex:GantryRobotCalibratingModeMetric aic:hasUnit "W"^^xsd:string .
            
            ex:Maintenance a aic:OperationMode .
            ex:Maintenance aic:hasModeMetric ex:GantryRobotMaintenanceModeMetric .
            ex:GantryRobotMaintenanceModeMetric aic:hasValue "3.52"^^xsd:decimal .
            ex:GantryRobotMaintenanceModeMetric aic:hasUnit "W"^^xsd:string .
            
            {subject_iri} aic:isInOperationMode ex:Idle .
            
            {temp_informationID_1} rdf:reifies << {subject_iri} aic:isInOperationMode ex:Idle >> .
            {temp_informationID_1} aic:validFrom "{point_in_time}"^^xsd:dateTime .
            {temp_informationID_1} aic:hasInformationType aic:Performed .
            {temp_informationID_1} aic:generatedBy {generated_by_iri} {informationTypeString}.
            
            {subject_iri} aic:isOperatingIn ex:RestingPosition .
            ex:RestingPosition a aic:Zone .

            {temp_informationID_2} rdf:reifies << {subject_iri} aic:isOperatingIn ex:RestingPosition >> .
            {temp_informationID_2} aic:validFrom "{point_in_time}"^^xsd:dateTime .
            {temp_informationID_2} aic:hasInformationType aic:Performed .
            {temp_informationID_2} aic:generatedBy {generated_by_iri} {informationTypeString}.
        }}
        WHERE {{
            FILTER NOT EXISTS {{
                {subject_iri} aic:isInOperationMode ex:Idle .
                {subject_iri} aic:isOperatingIn ex:RestingPosition .
            }}
        }}
        """
        
    
          
    if queryType == "insert-rigid":
        
        temp_informationID_1 = _ex(generateInformationID())
        temp_informationID_2 = _ex(generateInformationID())
         
        sparql_query = sparqlPrefix + f"""
        INSERT {{
            {objectClassStringInsert}
            {subject_iri} {predicate_iri} {object_iri} .
            {temp_informationID_1} rdf:reifies << {subject_iri} {predicate_iri} {object_iri} >> .
            {temp_informationID_1} aic:validFrom ?T .
            {temp_informationID_1} aic:hasInformationType aic:Performed .
            {temp_informationID_1} aic:generatedBy {generated_by_iri} {informationTypeString}.
            {temp_informationID_2} rdf:reifies << {subject_iri} {predicate_iri} ?object >> .
            {temp_informationID_2} aic:validUntil ?T .
            {temp_informationID_2} aic:hasInformationType aic:Performed .
            {temp_informationID_2} aic:generatedBy aic:{thisAgentID} {informationTypeString}.
        }}
        WHERE {{
        SELECT ?object ?from (MIN(?toCandidate) AS ?to) ?T
        WHERE {{
            BIND(xsd:dateTime("{point_in_time}") AS ?T)
          
            ?informationID_3 rdf:reifies << {subject_iri} {predicate_iri} ?object >> .
            ?informationID_3 aic:validFrom ?from {informationTypeString}.
            
            FILTER(?from <= ?T)

            OPTIONAL {{
                ?informationID_4 rdf:reifies << {subject_iri} {predicate_iri} ?object >> .
                ?informationID_4 aic:validUntil ?toCandidate {informationTypeString}.
                FILTER(?toCandidate > ?from)
            }}
        }}
        GROUP BY ?object ?from ?T
        ORDER BY DESC(?from)
        LIMIT 1
        }}
        """
        
    if queryType == "insert-flexible-start":
        
        temp_informationID_1 = _ex(generateInformationID())
                
        sparql_query = sparqlPrefix + f"""
        INSERT {{
            {subject_iri} {predicate_iri} {object_iri} .
            {objectClassStringInsert}
            {temp_informationID_1} rdf:reifies << {subject_iri} {predicate_iri} {object_iri} >> .
            {temp_informationID_1} aic:validFrom "{point_in_time}"^^xsd:dateTime .
            {temp_informationID_1} aic:hasInformationType aic:Performed .
            {temp_informationID_1} aic:generatedBy {generated_by_iri} {informationTypeString}.
        }}
        WHERE {{
            FILTER NOT EXISTS {{             
                ?informationID_2 rdf:reifies << {subject_iri} {predicate_iri} {object_iri} >> .
                ?informationID_2 aic:validFrom ?tOpen {informationTypeString}.
                FILTER (?tOpen <= "{point_in_time}"^^xsd:dateTime)

                FILTER NOT EXISTS {{
                ?informationID_3 rdf:reifies << {subject_iri} {predicate_iri} {object_iri} >> .
                ?informationID_3 aic:validUntil ?tClose {informationTypeString}.
                FILTER (?tClose >= ?tOpen && ?tClose <= "{point_in_time}"^^xsd:dateTime)
                }}
            }}
        }}
        """
                 
    if queryType == "insert-flexible-stop":
        
        temp_informationID_1 = _ex(generateInformationID())
        
        sparql_query = sparqlPrefix + f"""
        INSERT {{
            {temp_informationID_1} rdf:reifies << {subject_iri} {predicate_iri} {object_iri} >> .
            {temp_informationID_1} aic:validUntil "{point_in_time}"^^xsd:dateTime .
            {temp_informationID_1} aic:hasInformationType aic:Performed .
            {temp_informationID_1} aic:generatedBy {generated_by_iri} {informationTypeString}.
        }}
        WHERE {{
                ?informationID_2 rdf:reifies << {subject_iri} {predicate_iri} {object_iri} >> .
                ?informationID_2 aic:validFrom ?fromTime {informationTypeString}.
                FILTER ( ?fromTime <= "{point_in_time}"^^xsd:dateTime )
                FILTER NOT EXISTS {{
                    ?informationID_3 rdf:reifies << {subject_iri} {predicate_iri} {object_iri} >> .
                    ?informationID_3 aic:validUntil ?anyTo {informationTypeString}.
                    FILTER (?fromTime <= ?anyTo)
                }}

        }}
        """
    
    if queryType == "insert-event":
        
        temp_informationID_1 = _ex(generateInformationID())
        
        sparql_query = sparqlPrefix + f"""
        INSERT DATA {{
            {objectClassStringInsert}
            {subject_iri} {predicate_iri} {object_iri} .
            {temp_informationID_1} rdf:reifies << {subject_iri} {predicate_iri} {object_iri} >> .
            {temp_informationID_1} aic:validAt "{point_in_time}"^^xsd:dateTime .
            {temp_informationID_1} aic:hasInformationType aic:Performed .
            {temp_informationID_1} aic:generatedBy {generated_by_iri} {informationTypeString}.
        }}
        """  
        
            
    if queryType == "select-valid-rigid":
        sparql_query = sparqlPrefix + f"""       
        SELECT ?subject ?object ?validFrom ?informationID_validFrom ?validUntil ?informationID_validUntil
        WHERE {{
            BIND(xsd:dateTime("{point_in_time}") AS ?T)
            
            {subject_bind_string}

            ?informationID_validFrom rdf:reifies << ?subject {predicate_iri} ?object >> .
            ?informationID_validFrom aic:validFrom ?validFrom {informationTypeString}.
            FILTER(?validFrom <= ?T)

            # Map that min to its id2
            OPTIONAL {{
                {{
                SELECT ?subject ?object ?validFrom ?informationID_validFrom (MIN(?validUntil1) AS ?validUntil)
                WHERE {{
                    ?informationID_validFrom rdf:reifies << ?subject {predicate_iri} ?object >> .
                    ?informationID_validFrom aic:validFrom ?validFrom {informationTypeString}.
                    
                        ?informationID_validUntil rdf:reifies << ?subject {predicate_iri} ?object >> .
                        ?informationID_validUntil aic:validUntil ?validUntil1 {informationTypeString}.
                        FILTER(?validUntil1 > ?validFrom) .
                }}
                GROUP BY ?subject ?object ?validFrom ?informationID_validFrom
            }}
                ?informationID_validUntil rdf:reifies << ?subject {predicate_iri} ?object >> .
                ?informationID_validUntil aic:validUntil ?validUntil {informationTypeString}.
            }}
        }}
        ORDER BY DESC(?validFrom)
        LIMIT 1
        """


    if queryType == "select-valid-flexible":
        sparql_query = sparqlPrefix + f"""
        SELECT ?subject ?object ?validFrom ?informationID_validFrom ?validUntil ?informationID_validUntil ?objectClass
        WHERE {{
        {subject_bind_string}
        ?subject {predicate_iri} ?object .
        ?object a ?objectClass .
        {objectClassStringSelect}

        ?informationID_validFrom rdf:reifies << ?subject {predicate_iri} ?object >> .
        ?informationID_validFrom aic:validFrom ?validFrom {informationTypeString}.
        FILTER (?validFrom <= xsd:dateTime("{point_in_time}"))
        FILTER NOT EXISTS {{
            ?informationID_1 rdf:reifies << ?subject {predicate_iri} ?object >> .
            ?informationID_1 aic:validFrom ?laterStart {informationTypeString}.
            FILTER (?laterStart <= xsd:dateTime("{point_in_time}") && ?laterStart > ?validFrom)
        }}
        
        OPTIONAL {{
            ?informationID_validUntil rdf:reifies << ?subject {predicate_iri} ?object >> .
            ?informationID_validUntil aic:validUntil ?validUntil {informationTypeString}.
            FILTER (?validUntil >= ?validFrom)
            FILTER NOT EXISTS {{
            ?informationID_2 rdf:reifies << ?subject {predicate_iri} ?object >> .
            ?informationID_2 aic:validUntil ?earlierStop {informationTypeString}.
            FILTER (?validFrom <= ?earlierStop  && ?earlierStop < ?validUntil)
            }}
        }}

        FILTER ( !BOUND(?validUntil) || xsd:dateTime("{point_in_time}") < ?validUntil )
        }}
        ORDER BY DESC(?validFrom)
        """
    
       
    if queryType == "select-past-rigid":
        sparql_query = sparqlPrefix + f"""       
        SELECT ?subject ?object ?validFrom ?informationID_validFrom ?validUntil ?informationID_validUntil
        WHERE {{
            BIND(xsd:dateTime("{point_in_time}") AS ?T)
            
            {subject_bind_string}

            ?informationID_validFrom rdf:reifies << ?subject {predicate_iri} ?object >> .
            ?informationID_validFrom aic:validFrom ?validFrom {informationTypeString}.
            FILTER(?validFrom <= ?T)

            # Map that min to its id2
            OPTIONAL {{
                {{
                SELECT ?subject ?object ?validFrom ?informationID_validFrom (MIN(?validUntil1) AS ?validUntil)
                WHERE {{
                    ?informationID_validFrom rdf:reifies << ?subject {predicate_iri} ?object >> .
                    ?informationID_validFrom aic:validFrom ?validFrom {informationTypeString}.
                    
                        ?informationID_validUntil rdf:reifies << ?subject {predicate_iri} ?object >> .
                        ?informationID_validUntil aic:validUntil ?validUntil1 {informationTypeString}.
                        FILTER(?validUntil1 > ?validFrom) .
                }}
                GROUP BY ?subject ?object ?validFrom ?informationID_validFrom
            }}
                ?informationID_validUntil rdf:reifies << ?subject {predicate_iri} ?object >> .
                ?informationID_validUntil aic:validUntil ?validUntil {informationTypeString}.
            }}
        }}
        ORDER BY DESC(?validFrom)
        """
 
        

    if queryType == "select-past-flexible":
        sparql_query = sparqlPrefix + f"""     
        SELECT ?subject ?object ?validFrom ?informationID_validFrom ?validUntil ?informationID_validUntil ?objectClass 
        WHERE {{
            BIND(xsd:dateTime("{point_in_time}") AS ?now)
            {object_bind_string}
            ?subject {predicate_iri} ?object .
            ?object a ?objectClass .
            
            ?informationID_validFrom rdf:reifies << ?subject {predicate_iri} ?object >> .
            ?informationID_validFrom aic:validFrom ?validFrom {informationTypeString}.
            FILTER (?validFrom <= ?now)

            OPTIONAL {{
                {{
                    SELECT ?subject ?object ?informationID_validFrom ?validFrom (MIN(?in1) AS ?validUntil)
                    WHERE {{
                        ?informationID_validFrom rdf:reifies << ?subject {predicate_iri} ?object >> .
                        ?informationID_validFrom aic:validFrom ?validFrom {informationTypeString}.
                        ?informationID_1 rdf:reifies << ?subject {predicate_iri} ?object >> .
                        ?informationID_1 aic:validUntil ?in1 {informationTypeString}.
                        FILTER (?in1 <= ?now)
                        FILTER (?in1 >= ?validFrom)
                    }}
                    GROUP BY ?subject ?object ?informationID_validFrom ?validFrom
                }}

                ?informationID_validUntil rdf:reifies << ?subject {predicate_iri} ?object >> .
                ?informationID_validUntil aic:validUntil ?validUntil {informationTypeString}.
            }}
        }}
        ORDER BY DESC(?validFrom)
                """
        
       
    if queryType == "select-event":
        sparql_query = sparqlPrefix + f"""
        SELECT ?subject ?object ?validAt ?informationID_validAt
        WHERE {{
            ?subject {predicate_iri} ?object .
            
            ?informationID_validAt rdf:reifies << ?subject {predicate_iri} ?object >> .
            ?informationID_validAt aic:validAt ?validAt {informationTypeString}.
            FILTER (?validAt <= xsd:dateTime("{point_in_time}"))

        }}
        ORDER BY DESC(?validAt)
        """
        
        
    if queryType == "select-valid-resourceRequestsGantryRobot":
        sparql_query = sparqlPrefix + f"""
        SELECT ?subject ?object ?validFrom ?informationID_validFrom ?validUntil ?informationID_validUntil ?objectClass ?location 
        WHERE {{
        ?subject aic:requestsResource ?object .
        ?object a ?objectClass .
        {objectClassStringSelect}

        ?informationID_validFrom rdf:reifies << ?subject aic:requestsResource ?object >> .
        ?informationID_validFrom aic:validFrom ?validFrom {informationTypeString}.
        ?informationID_1 rdf:reifies << ?subject aic:isOperatingIn ?location >> .
        ?informationID_1 aic:validAt ?validFrom {informationTypeString}.
        FILTER (?validFrom <= xsd:dateTime("{point_in_time}"))
        FILTER NOT EXISTS {{
            ?informationID_2 rdf:reifies << ?subject aic:requestsResource ?object >> .
            ?informationID_2 aic:validFrom ?laterStart {informationTypeString}.
            FILTER (?laterStart <= xsd:dateTime("{point_in_time}") && ?laterStart > ?validFrom)
        }}
        
        OPTIONAL {{
            ?informationID_validUntil rdf:reifies << ?subject aic:requestsResource ?object >> .
            ?informationID_validUntil aic:validUntil ?validUntil {informationTypeString}.
            FILTER (?validUntil >= ?validFrom)
            FILTER NOT EXISTS {{
            ?informationID_3 rdf:reifies << ?subject aic:requestsResource ?object >> .
            ?informationID_3 aic:validUntil ?earlierStop {informationTypeString}.
            FILTER (?validFrom <= ?earlierStop  && ?earlierStop < ?validUntil)
            }}
        }}

        FILTER ( !BOUND(?validUntil) || xsd:dateTime("{point_in_time}") < ?validUntil )
        }}
        ORDER BY DESC(?validFrom)
        """
        
    if queryType == "select-valid-resourceSuppliesGantryRobot":
        sparql_query = sparqlPrefix + f"""
        SELECT ?subject ?object ?validAt ?informationID_supply_validAt ?objectClass ?location
        WHERE {{
            ?subject aic:supplies ?object .
            ?object a ?objectClass .
            {objectClassStringSelect}

            ?informationID_supply_validAt rdf:reifies << ?subject aic:supplies ?object >> .
            ?informationID_supply_validAt aic:validAt ?validAt {informationTypeString}.
            
            ?informationID_location_validAt rdf:reifies << ?subject aic:isOperatingIn ?location >> .
            ?informationID_location_validAt aic:validAt ?validAt {informationTypeString}.
        FILTER (?validAt <= xsd:dateTime("{point_in_time}"))
        FILTER NOT EXISTS {{
            ?informationID_1 rdf:reifies << _ex(thisAgentID) aic:isOperatingIn ?location >> .
            ?informationID_1 aic:validFrom ?laterStart {informationTypeString}.
            FILTER (?laterStart >= ?validAt)
        }}
        }}
        ORDER BY DESC(?validAt)
        """
    
    if queryType == "reset-DB":
        sparql_query = sparqlPrefix + f"""
        DELETE {{
            ?s ?p ?o .
        }}
        WHERE {{
            ?s ?p ?o .
            FILTER(
                STRSTARTS(STR(?s), STR(ex:)) ||
                STRSTARTS(STR(?p), STR(ex:)) ||
                (isIRI(?o) && STRSTARTS(STR(?o), STR(ex:)))
            )
        }}
        """
    
    return sparql_query