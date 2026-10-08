import { useI18n } from "../I18n.jsx";

export default function RiskBadge({ tag }) {
  const { t } = useI18n();
  return <span className={`risk risk-${tag}`}>{t(`risk_${tag}`, `${tag} risk`)}</span>;
}
