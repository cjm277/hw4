// Yale campus photos used around the site. All are openly licensed on Wikimedia Commons, show no people,
// and are loaded from Wikimedia (credited in the footer and in output/design.md).

export type CampusPhoto = {
  src: string
  alt: string
  credit: string
  license: string
  source: string
}

const commons = (path: string, width: number) =>
  `https://upload.wikimedia.org/wikipedia/commons/thumb/${path}/${width}px-${path.split('/').pop()}`

export const PHOTOS = {
  harkness: {
    src: commons('7/72/Harkness_Tower_Highsmith.jpg', 1280),
    alt: 'Harkness Tower rising over Yale’s Collegiate Gothic stonework against a blue sky',
    credit: 'Carol M. Highsmith, Library of Congress',
    license: 'Public domain',
    source: 'https://commons.wikimedia.org/wiki/File:Harkness_Tower_Highsmith.jpg',
  },
  yaleBowl: {
    src: commons('c/ce/Yale_Bowl_aerial_view_2023_%28Quintin_Soloviev%29.jpg', 1920),
    alt: 'Aerial view of the Yale Bowl with YALE painted in both end zones',
    credit: 'Quintin Soloviev',
    license: 'CC BY 4.0',
    source: 'https://commons.wikimedia.org/wiki/File:Yale_Bowl_aerial_view_2023_(Quintin_Soloviev).jpg',
  },
  lawSchool: {
    src: commons('4/41/Sterling_Law_Building%2C_Yale_Law_School.jpg', 1920),
    alt: 'The Gothic front entrance of the Sterling Law Building, home of Yale Law School',
    credit: 'Kenneth C. Zirkel',
    license: 'CC BY-SA 4.0',
    source: 'https://commons.wikimedia.org/wiki/File:Sterling_Law_Building,_Yale_Law_School.jpg',
  },
  lawTowers: {
    src: commons('0/0b/Sterling_Law_Building%2C_Yale.jpg', 1280),
    alt: 'The stone towers of the Sterling Law Building against a cloudy blue sky',
    credit: 'Wikimedia Commons contributor',
    license: 'Public domain',
    source: 'https://commons.wikimedia.org/wiki/File:Sterling_Law_Building,_Yale.jpg',
  },
  sterlingLibrary: {
    src: commons('e/ee/Sterling_Memorial_Library_seen_from_the_front%2C_Yale_University%2C_New_Haven%2C_Connecticut.jpg', 1920),
    alt: 'The front of Sterling Memorial Library, Yale’s Gothic cathedral of books',
    credit: 'Christian David',
    license: 'CC BY-SA 4.0',
    source:
      'https://commons.wikimedia.org/wiki/File:Sterling_Memorial_Library_seen_from_the_front,_Yale_University,_New_Haven,_Connecticut.jpg',
  },
} satisfies Record<string, CampusPhoto>

export const PHOTO_LIST: CampusPhoto[] = Object.values(PHOTOS)
