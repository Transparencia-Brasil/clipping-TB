#' Paleta de cores Transparência Brasil
cores_tb <- c(
  laranja = "#F6A323",
  cinza_escuro = "#1d1d1b",
  cinza_claro = "#6f7171",
  cinza_quase_branco = "#ececec",
  azul = "#41ACBD"
)

#' Paleta de cores Achados e pedidos
cores_aep <- c(
  laranja = "#fcaa27",
  rosa = "#D81755",
  cinza = "#969696",
  marrom = "#B27D5C"
)

# uso de fontes e plot-aesthetics
library(ggplot2)
hrbrthemes::import_roboto_condensed()
extrafont::loadfonts()
ggplot2::theme_set(hrbrthemes::theme_ipsum_rc())

theme_update(
  panel.grid.minor = element_blank(),
  panel.background = element_rect(fill = "gray97", color = "transparent"),
  axis.line.y = element_blank(),
  axis.line.x = element_line(color = "gray30"),
  text = element_text(family = "Roboto Condensed"),
  panel.grid.major.x = element_blank(),
  panel.grid.major.y = element_line(color = "gray60")
)

# helper functions:

reais <- function(x) {
  scales::dollar(
    x,
    prefix = "R$ ",
    accuracy = 1.0,
    big.mark = ".",
    decimal.mark = ","
  )
}

reais_milhoes <- function(x) {
  scales::number(
    x / 1e6,
    prefix = "R$ ",
    big.mark = ".",
    decimal.mark = ",",
    suffix = "Mi",
    accuracy = 0.100
  )
}

hrbrthemes::update_geom_font_defaults(
  color = "gray30",
  family = "Roboto Condensed"
)
