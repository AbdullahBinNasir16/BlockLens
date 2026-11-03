import { useInView } from '../../lib/hooks';
import { useProvenance, useSampleReason } from '../../lib/project-context';
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

/** Marks a section as live or sample, on the section itself. Research
 *  sections are never live (Phase 7): sourced ones are a dated snapshot,
 *  the rest illustrative, and the chip says which. */
export function ProvenanceChip({ section }: { section: string }) {
  const live = useProvenance(section) === 'live';
  const why = useSampleReason(section);
  return (
    <ProvChip
      live={live}
      why={why}
      note={
        live
          ? 'Fetched live through the BlockLens API.'
          : why.startsWith('snapshot')
            ? 'Captured from public sources on that date and frozen. It is not refreshed.'
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
