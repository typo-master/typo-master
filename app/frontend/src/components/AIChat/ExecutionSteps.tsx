import { Tag, Typography } from "antd";
import {
  ApiOutlined,
  BranchesOutlined,
  CheckCircleOutlined,
  CheckOutlined,
  CloseCircleOutlined,
  DotChartOutlined,
  LoadingOutlined,
  PlayCircleOutlined,
  SettingOutlined,
  ToolOutlined,
} from "@ant-design/icons";
import type { ExecutionStep } from "../../db";
import styles from "./ExecutionSteps.module.css";

const { Text } = Typography;

interface ExecutionStepsProps {
  steps: ExecutionStep[];
}

export default function ExecutionSteps({ steps }: ExecutionStepsProps) {
  const getStepIcon = (icon: string, status: ExecutionStep["status"]) => {
    const iconStyle = { fontSize: 14 };
    const spin = status === "running";
    switch (icon) {
      case "tool": return spin ? <LoadingOutlined style={iconStyle} spin /> : <ToolOutlined style={iconStyle} />;
      case "shield": return spin ? <LoadingOutlined style={iconStyle} spin /> : <ApiOutlined style={iconStyle} />;
      case "setting": return spin ? <LoadingOutlined style={iconStyle} spin /> : <SettingOutlined style={iconStyle} />;
      case "play": return spin ? <LoadingOutlined style={iconStyle} spin /> : <PlayCircleOutlined style={iconStyle} />;
      case "result": return spin ? <LoadingOutlined style={iconStyle} spin /> : <DotChartOutlined style={iconStyle} />;
      default: return spin ? <LoadingOutlined style={iconStyle} spin /> : <CheckCircleOutlined style={iconStyle} />;
    }
  };

  const getStepColor = (status: ExecutionStep["status"]) => {
    switch (status) {
      case "completed": return "#22c55e";
      case "running": return "#3b82f6";
      case "failed": return "#ef4444";
      default: return "#94a3b8";
    }
  };

  const completedCount = steps.filter((s) => s.status === "completed").length;
  const runningCount = steps.filter((s) => s.status === "running").length;
  const failedCount = steps.filter((s) => s.status === "failed").length;

  const totalProgress = steps.reduce((sum, step) => {
    if (step.status === "completed") return sum + 100;
    if (step.status === "running") return sum + (step.progress || 50);
    return sum;
  }, 0) / steps.length;

  return (
    <div className={styles.container}>
      <div className={styles.progressHeader}>
        <Text className={styles.progressLabel}>
          <BranchesOutlined /> 执行进度
        </Text>
        <Text className={styles.progressInfo}>
          {completedCount}/{steps.length} 完成
          {failedCount > 0 && ` · ${failedCount} 失败`}
          {runningCount > 0 && ` · ${runningCount} 进行中`}
        </Text>
      </div>
      <div className={styles.progressBarTrack}>
        <div
          className={styles.progressBarFill}
          style={{
            width: `${totalProgress}%`,
            background: failedCount > 0
              ? "linear-gradient(90deg, #22c55e, #f59e0b)"
              : "linear-gradient(90deg, #22c55e, #4ade80)",
          }}
        />
      </div>

      <div className={styles.stepList}>
        {steps.map((step) => {
          const color = getStepColor(step.status);
          return (
            <div key={step.id} className={styles.stepItem}>
              <div
                className={styles.stepIcon}
                style={{
                  background: step.status === "pending" ? "#f1f5f9" : `${color}15`,
                  borderColor: step.status === "pending" ? "#cbd5e1" : color,
                  color: step.status === "pending" ? "#94a3b8" : color,
                }}
              >
                {step.status === "completed" ? (
                  <CheckOutlined style={{ fontSize: 12, fontWeight: "bold" }} />
                ) : step.status === "failed" ? (
                  <CloseCircleOutlined style={{ fontSize: 12 }} />
                ) : (
                  getStepIcon(step.icon || "", step.status)
                )}
              </div>

              <div className={styles.stepContent}>
                <div className={styles.stepTitleRow}>
                  <Text
                    className={styles.stepTitle}
                    style={{
                      fontWeight: step.status === "running" ? 600 : 500,
                      color: step.status === "pending" ? "#64748b" : "#1e293b",
                    }}
                  >
                    {step.name}
                  </Text>
                  {step.status === "running" && (
                    <Tag color="processing" className={styles.stepTag}>进行中</Tag>
                  )}
                  {step.status === "failed" && (
                    <Tag color="error" className={styles.stepTag}>失败</Tag>
                  )}
                </div>
                {step.description && step.status !== "pending" && (
                  <Text className={styles.stepDesc}>{step.description}</Text>
                )}
                {step.subSteps && step.subSteps.length > 0 && step.status !== "pending" && (
                  <div className={styles.subStepList}>
                    {step.subSteps.map((subStep) => (
                      <div key={subStep.id} className={styles.subStepItem}>
                        <div
                          className={styles.subStepDot}
                          style={{ background: getStepColor(subStep.status) }}
                        />
                        <Text className={styles.subStepText}>{subStep.name}</Text>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {step.status === "completed" && step.endTime && step.startTime && (
                <Text className={styles.stepDuration}>
                  {((step.endTime - step.startTime) / 1000).toFixed(1)}s
                </Text>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
