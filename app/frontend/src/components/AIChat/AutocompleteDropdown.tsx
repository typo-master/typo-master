import { Typography } from "antd";
import type { AgentSkill } from "../../db";
import styles from "./AutocompleteDropdown.module.css";

const { Text } = Typography;

export interface SlashCommand {
  name: string;
  description: string;
  icon: React.ReactNode;
  usage?: string;
}

export type AutocompleteType = "command" | "skill" | null;

interface AutocompleteDropdownProps {
  visible: boolean;
  type: AutocompleteType;
  commands: SlashCommand[];
  skills: AgentSkill[];
  selectedIndex: number;
  onSelect: (index: number) => void;
  onMouseEnter: (index: number) => void;
}

export default function AutocompleteDropdown({
  visible,
  type,
  commands,
  skills,
  selectedIndex,
  onSelect,
  onMouseEnter,
}: AutocompleteDropdownProps) {
  if (!visible) return null;

  return (
    <div className={styles.dropdown}>
      {type === "command" && (
        <>
          <div className={styles.sectionHeader}>
            可用命令 ({commands.length})
          </div>
          {commands.map((cmd, index) => (
            <div
              key={cmd.name}
              className={`${styles.item} ${index === selectedIndex ? styles.itemSelected : ""}`}
              onClick={() => onSelect(index)}
              onMouseEnter={() => onMouseEnter(index)}
            >
              <span className={styles.itemIcon}>{cmd.icon}</span>
              <div className={styles.itemContent}>
                <div className={styles.itemTitleRow}>
                  <Text strong className={styles.itemName}>/{cmd.name}</Text>
                  <Text className={styles.itemDesc}>{cmd.description}</Text>
                </div>
                {cmd.usage && (
                  <code className={styles.itemUsage}>{cmd.usage}</code>
                )}
              </div>
            </div>
          ))}
        </>
      )}

      {type === "skill" && (
        <>
          <div className={styles.sectionHeader}>
            可用技能 ({skills.length})
          </div>
          {skills.map((skill, index) => (
            <div
              key={skill.name}
              className={`${styles.item} ${index === selectedIndex ? styles.itemSelected : ""}`}
              onClick={() => onSelect(index)}
              onMouseEnter={() => onMouseEnter(index)}
            >
              <div className={styles.skillMeta}>
                <span className={styles.skillCategory}>{skill.category}</span>
                <Text strong className={styles.itemName}>{skill.name}</Text>
              </div>
              <Text className={styles.skillDescFull}>{skill.description}</Text>
              {skill.parameters && skill.parameters.length > 0 && (
                <div className={styles.paramList}>
                  {skill.parameters.slice(0, 3).map((param) => (
                    <span
                      key={param.name}
                      className={`${styles.paramTag} ${param.required ? styles.paramRequired : ""}`}
                    >
                      {param.name}
                      {param.required && <span className={styles.paramStar}>*</span>}
                    </span>
                  ))}
                  {skill.parameters.length > 3 && (
                    <span className={styles.paramMore}>+{skill.parameters.length - 3}</span>
                  )}
                </div>
              )}
            </div>
          ))}
        </>
      )}

      <div className={styles.footer}>
        <span className={styles.footerHint}>
          <kbd className={styles.kbd}>↑↓</kbd> 选择
        </span>
        <span className={styles.footerHint}>
          <kbd className={styles.kbd}>↵</kbd> 确认
        </span>
        <span className={styles.footerHint}>
          <kbd className={styles.kbd}>Tab</kbd> 补全
        </span>
        <span className={styles.footerHint}>
          <kbd className={styles.kbd}>Esc</kbd> 关闭
        </span>
      </div>
    </div>
  );
}
