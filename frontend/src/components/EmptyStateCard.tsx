import StateCardFrame from '@/components/StateCardFrame';

export default function EmptyStateCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return <StateCardFrame tone="empty" badge="空状态" title={title} description={description} />;
}