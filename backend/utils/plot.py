import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid")

# 1. Section C Data: Process Measures & Manipulation Checks
data_process = [
    # Temp = 0.5
    {
        "Temp": 0.5,
        "Measure": "Perceived Disagreement",
        "C1": 1.20,
        "C2": 1.93,
        "C3": 1.80,
    },
    {
        "Temp": 0.5,
        "Measure": "Perceived Breadth",
        "C1": 4.10,
        "C2": 5.40,
        "C3": 5.47,
    },
    {
        "Temp": 0.5,
        "Measure": "Cognitive Load",
        "C1": 3.20,
        "C2": 3.70,
        "C3": 3.80,
    },
    {
        "Temp": 0.5,
        "Measure": "Perceived Confusion",
        "C1": 2.07,
        "C2": 2.43,
        "C3": 2.43,
    },
    {
        "Temp": 0.5,
        "Measure": "Trust in Advice",
        "C1": 6.00,
        "C2": 6.00,
        "C3": 6.00,
    },
    {"Temp": 0.5, "Measure": "Confidence", "C1": 5.23, "C2": 5.10, "C3": 5.17},
    {"Temp": 0.5, "Measure": "Ownership", "C1": 4.30, "C2": 4.37, "C3": 4.33},
    # Temp = 0.7
    {
        "Temp": 0.7,
        "Measure": "Perceived Disagreement",
        "C1": 1.10,
        "C2": 2.10,
        "C3": 1.90,
    },
    {
        "Temp": 0.7,
        "Measure": "Perceived Breadth",
        "C1": 4.27,
        "C2": 5.43,
        "C3": 5.63,
    },
    {
        "Temp": 0.7,
        "Measure": "Cognitive Load",
        "C1": 3.13,
        "C2": 3.80,
        "C3": 3.87,
    },
    {
        "Temp": 0.7,
        "Measure": "Perceived Confusion",
        "C1": 2.03,
        "C2": 2.53,
        "C3": 2.50,
    },
    {
        "Temp": 0.7,
        "Measure": "Trust in Advice",
        "C1": 6.00,
        "C2": 5.97,
        "C3": 5.97,
    },
    {"Temp": 0.7, "Measure": "Confidence", "C1": 5.20, "C2": 5.07, "C3": 5.30},
    {"Temp": 0.7, "Measure": "Ownership", "C1": 4.50, "C2": 4.43, "C3": 4.50},
    {
        "Temp": 1.0,
        "Measure": "Perceived Disagreement",
        "C1": 1.13,
        "C2": 1.90,
        "C3": 2.03,
    },
    {
        "Temp": 1.0,
        "Measure": "Perceived Breadth",
        "C1": 4.40,
        "C2": 5.37,
        "C3": 5.47,
    },
    {
        "Temp": 1.0,
        "Measure": "Cognitive Load",
        "C1": 3.07,
        "C2": 3.90,
        "C3": 3.70,
    },
    {
        "Temp": 1.0,
        "Measure": "Perceived Confusion",
        "C1": 1.97,
        "C2": 2.43,
        "C3": 2.47,
    },
    {
        "Temp": 1.0,
        "Measure": "Trust in Advice",
        "C1": 6.03,
        "C2": 5.97,
        "C3": 6.00,
    },
    {"Temp": 1.0, "Measure": "Confidence", "C1": 5.17, "C2": 5.17, "C3": 5.10},
    {"Temp": 1.0, "Measure": "Ownership", "C1": 4.40, "C2": 4.23, "C3": 4.33},
    # Temp = 1.2
    {
        "Temp": 1.2,
        "Measure": "Perceived Disagreement",
        "C1": 1.33,
        "C2": 1.97,
        "C3": 1.87,
    },
    {
        "Temp": 1.2,
        "Measure": "Perceived Breadth",
        "C1": 4.50,
        "C2": 5.63,
        "C3": 5.83,
    },
    {
        "Temp": 1.2,
        "Measure": "Cognitive Load",
        "C1": 3.20,
        "C2": 4.20,
        "C3": 3.93,
    },
    {
        "Temp": 1.2,
        "Measure": "Perceived Confusion",
        "C1": 2.13,
        "C2": 2.73,
        "C3": 2.57,
    },
    {
        "Temp": 1.2,
        "Measure": "Trust in Advice",
        "C1": 6.03,
        "C2": 5.97,
        "C3": 5.97,
    },
    {"Temp": 1.2, "Measure": "Confidence", "C1": 5.20, "C2": 5.07, "C3": 5.13},
    {"Temp": 1.2, "Measure": "Ownership", "C1": 4.60, "C2": 4.30, "C3": 4.53},
]

# 2. Section D Data: Problem Formulation Quality
data_formulation = [
    # Temp = 0.5
    {"Temp": 0.5, "Measure": "Cause clarity", "C1": 2.74, "C2": 2.85, "C3": 2.45},
    {
        "Temp": 0.5,
        "Measure": "Causal evaluation",
        "C1": 1.93,
        "C2": 2.00,
        "C3": 2.38,
    },
    {
        "Temp": 0.5,
        "Measure": "Assumption identification",
        "C1": 1.30,
        "C2": 1.28,
        "C3": 1.38,
    },
    {
        "Temp": 0.5,
        "Measure": "Discriminating evidence",
        "C1": 1.35,
        "C2": 1.58,
        "C3": 1.43,
    },
    {
        "Temp": 0.5,
        "Measure": "Cause-action coherence",
        "C1": 2.51,
        "C2": 2.66,
        "C3": 2.86,
    },
    {
        "Temp": 0.5,
        "Measure": "Composite Score",
        "C1": 1.97,
        "C2": 2.08,
        "C3": 2.10,
    },
    {
        "Temp": 0.5,
        "Measure": "Comprehensiveness",
        "C1": 2.00,
        "C2": 2.50,
        "C3": 2.23,
    },
    {"Temp": 0.5, "Measure": "Novelty", "C1": 2.16, "C2": 2.08, "C3": 2.11},
    # Temp = 0.7
    {"Temp": 0.7, "Measure": "Cause clarity", "C1": 2.68, "C2": 2.68, "C3": 2.61},
    {
        "Temp": 0.7,
        "Measure": "Causal evaluation",
        "C1": 1.86,
        "C2": 2.19,
        "C3": 2.33,
    },
    {
        "Temp": 0.7,
        "Measure": "Assumption identification",
        "C1": 1.30,
        "C2": 1.20,
        "C3": 1.38,
    },
    {
        "Temp": 0.7,
        "Measure": "Discriminating evidence",
        "C1": 1.43,
        "C2": 1.29,
        "C3": 1.29,
    },
    {
        "Temp": 0.7,
        "Measure": "Cause-action coherence",
        "C1": 2.48,
        "C2": 2.64,
        "C3": 2.71,
    },
    {
        "Temp": 0.7,
        "Measure": "Composite Score",
        "C1": 1.95,
        "C2": 2.00,
        "C3": 2.07,
    },
    {
        "Temp": 0.7,
        "Measure": "Comprehensiveness",
        "C1": 2.07,
        "C2": 2.07,
        "C3": 2.40,
    },
    {"Temp": 0.7, "Measure": "Novelty", "C1": 2.08, "C2": 2.15, "C3": 2.14},
    {"Temp": 1.0, "Measure": "Cause clarity", "C1": 2.75, "C2": 2.69, "C3": 2.74},
    {
        "Temp": 1.0,
        "Measure": "Causal evaluation",
        "C1": 2.15,
        "C2": 2.19,
        "C3": 2.28,
    },
    {
        "Temp": 1.0,
        "Measure": "Assumption identification",
        "C1": 1.28,
        "C2": 1.22,
        "C3": 1.40,
    },
    {
        "Temp": 1.0,
        "Measure": "Discriminating evidence",
        "C1": 1.48,
        "C2": 1.37,
        "C3": 1.32,
    },
    {
        "Temp": 1.0,
        "Measure": "Cause-action coherence",
        "C1": 2.42,
        "C2": 2.64,
        "C3": 2.79,
    },
    {
        "Temp": 1.0,
        "Measure": "Composite Score",
        "C1": 2.02,
        "C2": 2.02,
        "C3": 2.11,
    },
    {
        "Temp": 1.0,
        "Measure": "Comprehensiveness",
        "C1": 2.43,
        "C2": 2.37,
        "C3": 2.13,
    },
    {"Temp": 1.0, "Measure": "Novelty", "C1": 2.09, "C2": 2.09, "C3": 2.08},
    # Temp = 1.2
    {"Temp": 1.2, "Measure": "Cause clarity", "C1": 2.62, "C2": 2.81, "C3": 2.71},
    {
        "Temp": 1.2,
        "Measure": "Causal evaluation",
        "C1": 2.00,
        "C2": 2.18,
        "C3": 2.24,
    },
    {
        "Temp": 1.2,
        "Measure": "Assumption identification",
        "C1": 1.28,
        "C2": 1.22,
        "C3": 1.32,
    },
    {
        "Temp": 1.2,
        "Measure": "Discriminating evidence",
        "C1": 1.29,
        "C2": 1.56,
        "C3": 1.37,
    },
    {
        "Temp": 1.2,
        "Measure": "Cause-action coherence",
        "C1": 2.60,
        "C2": 2.59,
        "C3": 2.67,
    },
    {
        "Temp": 1.2,
        "Measure": "Composite Score",
        "C1": 1.96,
        "C2": 2.07,
        "C3": 2.06,
    },
    {
        "Temp": 1.2,
        "Measure": "Comprehensiveness",
        "C1": 2.10,
        "C2": 2.27,
        "C3": 2.50,
    },
    {"Temp": 1.2, "Measure": "Novelty", "C1": 2.12, "C2": 2.02, "C3": 2.13},
]

df_process = pd.DataFrame(data_process)
df_formulation = pd.DataFrame(data_formulation)


def plot_measures(df, title, filename):
    measures = df["Measure"].unique()
    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    axes = axes.flatten()

    for idx, measure in enumerate(measures):
        sub_df = df[df["Measure"] == measure].sort_values("Temp")
        ax = axes[idx]
        ax.plot(
            sub_df["Temp"],
            sub_df["C1"],
            marker="o",
            linewidth=2,
            label="C1 (Single)",
        )
        ax.plot(
            sub_df["Temp"],
            sub_df["C2"],
            marker="s",
            linewidth=2,
            label="C2 (Integrated)",
        )
        ax.plot(
            sub_df["Temp"],
            sub_df["C3"],
            marker="^",
            linewidth=2,
            label="C3 (Competing)",
        )

        ax.set_title(measure, fontsize=12, fontweight="bold")
        ax.set_xlabel("Temperature")
        ax.set_ylabel("Absolute Score")
        ax.set_xticks([0.5, 0.7, 1.0, 1.2])
        ax.legend()

    for j in range(len(measures), len(axes)):
        fig.delaxes(axes[j])

    fig.suptitle(title, fontsize=16, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(filename, bbox_inches="tight")
    plt.show()


plot_measures(
    df_process,
    "Process Measures & Manipulation Checks vs Temperature",
    "process_measures.png",
)
plot_measures(
    df_formulation,
    "Problem Formulation Quality vs Temperature",
    "formulation_quality.png",
)
