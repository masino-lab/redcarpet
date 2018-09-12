library(dplyr)
library(data.table)
library('RPostgreSQL')
library(getPass)
library(sqldf)

pg = dbDriver("PostgreSQL")
con = dbConnect(pg, user="masinoa", password=getPass::getPass(), host="reslndbhiops04.research.chop.edu", 
                port=5432, dbname="pbd_v24")

qry = "WITH SNOMED AS (
    SELECT concept_id, concept_name, vocabulary_id 
FROM vocabulary.concept 
WHERE vocabulary_id='SNOMED' AND domain_id='Condition' AND concept_class_id = 'Clinical Finding'
),

MEDRA AS (
SELECT concept_id, concept_name, vocabulary_id 
FROM vocabulary.concept 
WHERE vocabulary_id='MedDRA'AND domain_id='Condition'
),

SNOMED_2_MEDRA AS (
SELECT 	concept_id_1 snomed_id, 
concept_id_2 medra_id
FROM vocabulary.concept_relationship WHERE concept_id_1 IN (
SELECT concept_id from SNOMED
) AND relationship_id IN (
SELECT relationship_id FROM vocabulary.relationship WHERE
relationship_name like '%SNOMED%' and relationship_name like '%MedDRA%'
)
),

MEDRA_2_ICD9 AS (
SELECT 	concept_id_1 medra_id, 
concept_id_2 icd9_id,
relationship_id med2icd_relation
FROM vocabulary.concept_relationship WHERE concept_id_1 IN (
SELECT concept_id from MEDRA
) AND relationship_id IN (
SELECT relationship_id FROM vocabulary.relationship WHERE
relationship_name like '%ICD%' and relationship_name like '%MedDRA%'
)
),

SNOMED_2_MEDRA_2_ICD9 AS (
SELECT 	snomed_id,
tbl1.medra_id,
icd9_id,
med2icd_relation
FROM SNOMED_2_MEDRA tbl1 
INNER JOIN MEDRA_2_ICD9 tbl2 
ON tbl1.medra_id = tbl2.medra_id
)

SELECT snomed_id,
medra_id,
icd9_id,
concept_name icd9_name
FROM SNOMED_2_MEDRA_2_ICD9 tbl1 
INNER JOIN vocabulary.concept tbl2
ON tbl1.icd9_id = tbl2.concept_id
ORDER BY snomed_id, medra_id
"

snomed_2_icd9 <- dbGetQuery(con, qry)
