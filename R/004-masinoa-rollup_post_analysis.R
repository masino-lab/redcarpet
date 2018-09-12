library(dplyr)
library(data.table)
library(ggplot2)
library(gridExtra)
library(cowplot)
library(stringr)

# constants
BASE_PC_CONDITIONS = 0
BASE_MC_CONDITIOSN = 1
out_dir = "/mnt/isilon/masino_lab/masinoa/pbd/PBD_O2.2_P1a_DeepLearning/analysis/output"

# set these values
# script assumes 001-masinoa-exploratory.rmd has been run and corresponding variables are available in R session
condition_file <- "input/pc_conditions_rolled.csv"

base_conditions <- BASE_PC_CONDITIONS
# -------------------------------------------------

tmp_conditions <- read.csv(condition_file)

# conditions-per-visit
tmp_conditions_per_visit <- tmp_conditions %>% count(person_id,visit_occurrence_id)
colnames(tmp_conditions_per_visit)[3] = "num_concepts"

# top-code-freq
tmp_freq <-data.frame(table(tmp_conditions$condition_concept_id))
colnames(tmp_freq)<-c("condition_concept_id", "freq")
tmp_freq <- tmp_freq %>% filter(freq>0)
tmp_freq <- tmp_freq[order(-tmp_freq$freq),]
t = sum(tmp_freq$freq)
tmp_freq <- mutate(tmp_freq, percent=freq/t*100)
tmp_freq[,3] <- cumsum(tmp_freq$percent)
colnames(tmp_freq)[3]<-"cum_percent"

## cum-dist-plot -------------------------------------------------------
if(base_conditions==BASE_PC_CONDITIONS){
  base_freq <- pc_freq
}else{
  base_freq <- mc_freq
}

plot.data <-rbind(data.frame(Population="Baseline", value=base_freq$cum_percent),
                  data.frame(Population="Rolled", value=tmp_freq$cum_percent))

plot.data <- plot.data %>% group_by(Population) %>% mutate(numValues = seq_len(n()))

t_tmp = sum(tmp_freq$freq)
eighty_percent_index_tmp = min(which(tmp_freq$cum_percent>=80))
eighty_percent_code_percent_tmp = eighty_percent_index_tmp / nrow(tmp_freq) * 100;

t_base = sum(base_freq$freq)
eighty_percent_index_base = min(which(base_freq$cum_percent>=80))
eighty_percent_code_percent_base = eighty_percent_index_base / nrow(base_freq) * 100;

xlimit = nrow(tmp_freq)+100
output_file = sprintf("%s/fig01_rollup_post_condition_concpets_cum.png",out_dir)
#pdf(output_file)
png(output_file, width = 900, height=600, res=125)
eighty_label_tmp=sprintf("%s%% of codes",format(eighty_percent_code_percent_tmp, digits=3))
eighty_label_base=sprintf("%s%% of codes",format(eighty_percent_code_percent_base, digits=3))

c1 = "#CC6666"
c2 = "steelblue"
#c1 = "gray35"
#c2 = "gray75"

tmp_cond_cum_plot <- ggplot(data=plot.data, aes(numValues, value, colour=Population)) + 
  geom_line()+
  scale_color_manual(values=c(c1,c2)) + 
  geom_hline(yintercept = 80, color="grey65")+
  geom_vline(xintercept = eighty_percent_index_base, color=c1)+
  annotate("label", x = eighty_percent_index_base, y = base_freq$cum_percent[eighty_percent_index_base]*1.07, label = eighty_label_base, color=c1) +
  geom_vline(xintercept = eighty_percent_index_tmp, color=c2)+
  annotate("label", x = eighty_percent_index_tmp, y = tmp_freq$cum_percent[eighty_percent_index_tmp]*1.07, label = eighty_label_tmp, color=c2) +
  scale_x_continuous(name="Condition Index (Most to least frequent)", breaks=union(1,union(seq(20,80,20),seq(100,nrow(plot.data),50))), limits=c(0, xlimit)) +
  scale_y_continuous(name="Cumulative Percent", breaks = seq(0,100, 5)) +
  ggtitle("Condition Code Usage")+
  theme_bw() +
  theme(plot.title = element_text(hjust = 0.5, size=14, face="bold"),
        axis.title = element_text(face="bold", size =14),
        axis.text.x = element_text(colour="black", size = 10),
        axis.text.y = element_text(colour="black", size = 10),
        legend.text = element_text(size = 10, colour = "black"),
        legend.background = element_rect(linetype="solid", colour="grey65"),
        legend.position = c(0.75, 0.2))
tmp_cond_cum_plot
dev.off()
tmp_cond_cum_plot

# top-k-dist-plot -----------------------------------
k=21

# build out the df with concept names
plot.data <- tmp_freq[1:k,]
plot.data <- plot.data %>% mutate(condition_concept_name=character(k))

for(rc in seq(1,k)){
  tmp <- snomed %>% filter(concept_id==plot.data$condition_concept_id[rc])
  ccn <- tmp$concept_name[1]
  plot.data$condition_concept_name[rc] <- ccn
}

size_by_k = 50
t = sum(tmp_freq$freq)
n_obs = nrow(tmp_freq)
ttl = sprintf("Primary Care Rollup\nMost Frequent Conditions (%s total)",n_obs)
output_file = sprintf("%s/fig02_rollup_post_topk_conditions.png",out_dir)  
png(output_file, width = 800, height=k*size_by_k, res=125)
tmp_top_k_bar <- ggplot(data=plot.data, aes(x=reorder(plot.data$condition_concept_name, plot.data$freq), y=plot.data$freq/t*100)) +
  geom_bar(stat="identity", width=.3, position = position_dodge(width=.6),fill="steelblue")+
  scale_x_discrete(name="Condition Concept Name", labels = function(x) str_wrap(x, width = 30)) +
  scale_y_continuous(name="Percentage of all documented conditions", breaks = seq(0,ceiling(plot.data$freq[1]/t*100), .5)) +
  ggtitle(ttl)+
  theme_bw() +
  theme(plot.title = element_text(hjust = 0.5, size=14, face="bold"),
        axis.title = element_text(face="bold", size =14),
        axis.text.x = element_text(colour="black", size = 10),
        axis.text.y = element_text(colour="black", size = 10))

tmp_top_k_bar + coord_flip()

dev.off()

tmp_top_k_bar+ coord_flip()

#calc-novel-condition-counts
tmp_visit_count <-length(unique(tmp_conditions$visit_occurrence_id))
tmp_novel_condition_counts <- compile_novel_codes(tmp_conditions, tmp_visit_count, max_patient_conditions(tmp_conditions))

# novel-conditions-per-visit-boxplots
if(base_conditions==BASE_PC_CONDITIONS){
  base_cpv <- pc_conditions_per_visit
  base_ncc <- pc_novel_condition_counts
}else{
  base_cpv <- mc_conditions_per_visit
  base_ncc <- mc_novel_condition_counts
}

plot.data <-rbind(data.frame(Population="Total", X="Baseline", value=base_cpv$num_concepts),
                  data.frame(Population="Total", X="Rollup", value=tmp_conditions_per_visit$num_concepts),
                  data.frame(Population="Novel", X="Baseline", value=base_ncc$novel_conditions),
                  data.frame(Population="Novel", X="Rollup", value=tmp_novel_condition_counts$novel_conditions))

maxY = 20
fill <- "#4271AE"
line <- "#1F3552"
alpha = 0.7
output_file = sprintf("%s/fig03_rollup_post_conditions_per_visit_bp.pdf",out_dir)
pdf(output_file)
tmp_pc_bp <- ggplot(plot.data, aes(x=X, y=value)) +
  geom_boxplot(fill=fill, colour=line, alpha=alpha, outlier.alpha = 0.1) +
  coord_cartesian(ylim=c(0,maxY)) 

tmp_pc_bp <- tmp_pc_bp +
  scale_y_continuous(name="Condition Concepts", 
                     breaks = seq(0,maxY, 1)) +
  xlab("")+
  ggtitle("Condition Concepts Per Visit")+
  facet_grid(. ~ Population) +
  theme_bw() +
  theme(plot.title = element_text(hjust = 0.5, size=14, face="bold"),
        axis.title = element_text(colour="black", size =14),
        axis.text.x = element_text(colour="black", size = 12),
        axis.text.y = element_text(colour="black", size = 12),
        strip.text.x = element_text(colour="black", size = 12)) 

tmp_pc_bp
dev.off()
tmp_pc_bp

# remove data from workspace ----------------------------------------------------------
rm(maxY, fill, line, aplpha, tmp_pc_bp, plot.data, k, size_by_k, tmp, ccn, t, n_obs, ttl, output_file, pc_top_k_bar, rc)

rm( c1, c2, xlimit, tmp_cond_cum_plot, output_file, t_base, t_tmp, tmp_visit_count, tmp_novel_condition_counts)

rm(tmp_conditions, tmp_freq, base_freq, eighty_percent_index_tmp, eighty_percent_code_percent_tmp,eighty_label_tmp,eighty_label_base)
