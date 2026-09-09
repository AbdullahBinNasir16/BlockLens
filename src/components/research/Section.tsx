import { useInView } from '../../lib/hooks';
import { useProvenance } from '../../lib/project-context';
import { ProvChip, SectionHead } from '../primitives/Bits';

export interface SectionProps {
  id: string;
  index: string;
  title: string;
  sub?: string;
  right?: React.ReactNode;
  children: (seen: boolean) => React.ReactNode;
  wide?: boolean;
}

/** Marks whether a section's figures were fetched from a public source or
 *  are illustrative. With real projects on screen, that distinction has to
 *  be visible on the section itself, not buried in a footnote. */
export function ProvenanceChip({ section }: { section: string }) {
  const live = useProvenance(section) === 'live';
  return (
    <ProvChip
      live={live}
      note={
        live
          ? 'Figures in this section come from public sources — market data, the repository, or the project’s own site.'
          : 'Illustrative data. Shapes are representative; the numbers are not findings about this project.'
      }
    />
  );
}

/** Every research section shares one frame: a numbered head, a hairline,
 *  and a one-shot reveal when it first reaches the viewport. */
export function Section({ id, index, title, sub, right, children, wide }: SectionProps) {
  const [ref, seen] = useInView<HTMLElement>('0px 0px -8% 0px');

  return (
    <section className="bl-sec" id={id} ref={ref} data-seen={seen} data-wide={wide}>
      <SectionHead
        index={index}
        title={title}
        sub={sub}
        right={
          <>
            <ProvenanceChip section={id} />
            {right}
          </>
        }
      />
      <div className="bl-sec__body">{children(seen)}</div>
    </section>
  );
}

/** Titled sub-block inside a section. */
export function Block({
  title,
  note,
  children,
  span,
  pad = true,
}: {
  title?: string;
  note?: React.ReactNode;
  children: React.ReactNode;
  span?: number;
  pad?: boolean;
}) {
  return (
    <div className="bl-block" style={span ? { gridColumn: `span ${span}` } : undefined} data-pad={pad}>
      {(title || note) && (
        <div className="bl-block__h">
          {title && <span className="eyebrow eyebrow-ink">{title}</span>}
          {note && <span className="bl-block__note meta">{note}</span>}
        </div>
      )}
      {children}
    </div>
  );
}
