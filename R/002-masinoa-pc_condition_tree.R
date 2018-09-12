library(dplyr)
library(data.table)
library('RPostgreSQL')
library(getPass)
library(sqldf)

pg = dbDriver("PostgreSQL")
con = dbConnect(pg, user="masinoa", password=getPass::getPass(), host="reslndbhiops04.research.chop.edu", 
                port=5432, dbname="pbd_v24")

# CHANGE THESE PARAMETERS TO APPROPRIATE CONDITIONS TABLE / FILE
CONDITITIONS_DF_NAME <- "pc_conditions_with_visit_meta"
CONDITIONS_FILE = "/mnt/isilon/masino_lab/masinoa/pbd/PBD_O2.2_P1a_DeepLearning/analysis/output/pc_conditions_with_visit_meata.csv"
output_dir<-'/mnt/isilon/masino_lab/masinoa/pbd/PBD_O2.2_P1a_DeepLearning/analysis/output/rollup/primary_care_only'
tmp_condition_concept_unique_ids <- data.table(unique(pc_conditions$condition_concept_id))
# -------------------------------

LOAD_CONDITION_DATA = !exists(CONDITITIONS_DF_NAME)
if(LOAD_CONDITION_DATA){
  #primary care visit counts
  print("loading conditions from file ")
  read.csv(CONDITIONS_FILE)
}else{
  print("using conditions data already in workspace")
}

# create tmp table in DB with unique condition concept ids
colnames(tmp_condition_concept_unique_ids)[1]<-"condition_concept_id"
dbWriteTable(con, c("aim2_o2_2_p1","tmp_condition_ids"), value=tmp_condition_concept_unique_ids,overwrite=TRUE,row.names=FALSE)
rm(tmp_condition_concept_unique_ids)

# find max levels of separation between used codes and top ancestor
qry = " WITH SNOMED AS (
SELECT concept_id
FROM vocabulary.concept
WHERE vocabulary_id='SNOMED' AND domain_id='Condition' AND concept_class_id = 'Clinical Finding'
)

SELECT MAX(tbl3.min_levels_of_separation)
FROM (
SELECT 	tbl1.descendant_concept_id,
tbl2.concept_name descendant_concept_name,
tbl1.ancestor_concept_id, 
tbl1.min_levels_of_separation
FROM vocabulary.concept_ancestor tbl1 
INNER JOIN vocabulary.concept tbl2 ON
tbl1.descendant_concept_id = tbl2.concept_id
WHERE tbl1.descendant_concept_id IN (
SELECT DISTINCT(condition_concept_id) FROM aim2_o2_2_p1.tmp_condition_ids
) AND min_levels_of_separation>0 
AND tbl1.ancestor_concept_id IN (
SELECT concept_id FROM SNOMED
)
) AS tbl3 INNER JOIN vocabulary.concept tbl4 ON
tbl4.concept_id = tbl3.ancestor_concept_id"

max_levels <- dbGetQuery(con, qry)
max_levels <- max_levels$max

# get direct parents of used condition codes for primary care
qry="WITH SNOMED AS (
SELECT concept_id
FROM vocabulary.concept
WHERE vocabulary_id='SNOMED' AND domain_id='Condition' AND concept_class_id = 'Clinical Finding'
)

SELECT tbl3.descendant_concept_id concept_id,
tbl3.descendant_concept_name concept_name,
tbl3.ancestor_concept_id parent_concept_id,
tbl4.concept_name parent_concept_name
FROM (
SELECT 	tbl1.descendant_concept_id,
tbl2.concept_name descendant_concept_name,
tbl1.ancestor_concept_id, 
tbl1.min_levels_of_separation
FROM vocabulary.concept_ancestor tbl1 
INNER JOIN vocabulary.concept tbl2 ON
tbl1.descendant_concept_id = tbl2.concept_id
WHERE tbl1.descendant_concept_id IN (
SELECT DISTINCT(condition_concept_id) FROM aim2_o2_2_p1.tmp_condition_ids
) AND min_levels_of_separation=1 
AND tbl1.ancestor_concept_id IN (
SELECT concept_id FROM SNOMED
)
) AS tbl3 INNER JOIN vocabulary.concept tbl4 ON
tbl4.concept_id = tbl3.ancestor_concept_id"

conditions_parents<-dbGetQuery(con, qry)

# save to file
output_file<-sprintf("%s/level_0%s.csv",output_dir,1)
write.csv(conditions_parents, file = output_file,row.names=FALSE)

# write to temp table in DB to seed iteration
dbWriteTable(con, c("aim2_o2_2_p1","tmp"), value=conditions_parents,overwrite=TRUE,row.names=FALSE)

qry="WITH SNOMED AS (
SELECT concept_id
FROM vocabulary.concept
WHERE vocabulary_id='SNOMED' AND domain_id='Condition' AND concept_class_id = 'Clinical Finding'
)

SELECT tbl3.descendant_concept_id concept_id,
tbl3.descendant_concept_name concept_name,
tbl3.ancestor_concept_id parent_concept_id,
tbl4.concept_name parent_concept_name
FROM (
SELECT 	tbl1.descendant_concept_id,
tbl2.concept_name descendant_concept_name,
tbl1.ancestor_concept_id, 
tbl1.min_levels_of_separation
FROM vocabulary.concept_ancestor tbl1 
INNER JOIN vocabulary.concept tbl2 ON
tbl1.descendant_concept_id = tbl2.concept_id
WHERE tbl1.descendant_concept_id IN (
SELECT DISTINCT(parent_concept_id) FROM aim2_o2_2_p1.tmp
) AND min_levels_of_separation=1 
AND tbl1.ancestor_concept_id IN (
SELECT concept_id FROM SNOMED
)
) AS tbl3 INNER JOIN vocabulary.concept tbl4 ON
tbl4.concept_id = tbl3.ancestor_concept_id"

nextQuery=TRUE
k=2
while(nextQuery){
#for(k in seq(2,max_levels,1)){
  df<-dbGetQuery(con, qry)
  if(nrow(df)==0 | k>20){
    print(df[1:10,])
    nextQuery=FALSE
  }else{
    output_file<-sprintf("%s/level_%s.csv",output_dir,k)
    if(k<10){
      output_file<-sprintf("%s/level_0%s.csv",output_dir,k)
    }
    write.csv(df, file = output_file,row.names=FALSE)
    dbWriteTable(con, c("aim2_o2_2_p1","tmp"), value=df,overwrite=TRUE,row.names=FALSE)
    k=k+1
  }
}

sqldf("drop table if exists aim2_o2_2_p1.tmp;", connection=con)
sqldf("drop table if exists aim2_o2_2_p1.tmp_condition_ids;", connection=con)
