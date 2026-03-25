import { Empty, Button, Space, Typography } from "antd";
import { SearchOutlined } from "@ant-design/icons";

const { Text } = Typography;

interface EmptyResultProps {
  onClearFilters?: () => void;
}

export default function EmptyResult({ onClearFilters }: EmptyResultProps) {
  return (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description={
        <Space direction="vertical" size={8}>
          <Text strong>没有找到匹配的 Skill</Text>
          <Text type="secondary">尝试调整筛选条件或清除筛选</Text>
        </Space>
      }
    >
      {onClearFilters && (
        <Button type="primary" icon={<SearchOutlined />} onClick={onClearFilters}>
          清除全部筛选
        </Button>
      )}
    </Empty>
  );
}
