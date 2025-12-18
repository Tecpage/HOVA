// templates/indexierung_netto.typ — Indexierungsschreiben Nettomiete (Template)

import "../core/blocks.typ": recipient_block, handler_and_box, sep

let render_indexierung_netto(cfg) = [
  #page(
    background: image("../assets/logo.jpg", width: 21cm, height: 29.7cm)
  )[
    #v(3.8cm)

    #grid(
      columns: (1.6fr, 1.4fr),
      gutter: 3cm,
      [#recipient_block(cfg.recipient_lines)],
      [#handler_and_box(cfg.letter_date)],
    )

    #v(0.6cm)
    *Wertsicherung der Nettokaltmiete*

    #v(0.4cm)
    Sehr geehrte Damen und Herren, \

    auf Grundlage der vertraglich vereinbarten Wertsicherungsklausel
    informieren wir Sie über den Stand der Indexierung der Nettokaltmiete
    für das Mietverhältnis mit der **#cfg.tenant_name**. \

    Die Indexierung erfolgt auf Basis des Verbraucherpreisindex (VPI,
    Basisjahr 2020 = 100), **ausschließlich nach oben** und
    **erst bei Überschreiten einer Schwelle von mehr als #cfg.threshold_percent %**. \

    Ausgangsbasis ist eine monatliche Nettokaltmiete von
    **#cfg.base_net_amount #cfg.currency** mit Wirksamkeit ab **#cfg.effective_from**. \

    Derzeit ist die vertraglich vereinbarte Schwelle noch **nicht überschritten**,
    sodass keine Anpassung der Nettokaltmiete erfolgt. \

    Wir werden die Indexentwicklung weiterhin beobachten und Sie
    schriftlich informieren, sobald die Voraussetzungen für eine
    Mietanpassung erfüllt sind. \

    Die übrigen vertraglichen Regelungen bleiben unverändert.
  ]
]