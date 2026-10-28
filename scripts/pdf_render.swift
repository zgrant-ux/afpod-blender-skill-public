// pdf_render.swift <pdf> <page 1-based> <width px> <out.png> : transparent render of one PDF page
import PDFKit; import AppKit
let a = CommandLine.arguments
let doc = PDFDocument(url: URL(fileURLWithPath: a[1]))!; let p = doc.page(at: Int(a[2])! - 1)!
let b = p.bounds(for: .mediaBox); let W = Int(a[3])!; let s = CGFloat(W) / b.width; let H = Int(b.height * s)
let cs = CGColorSpace(name: CGColorSpace.sRGB)!
let ctx = CGContext(data: nil, width: W, height: H, bitsPerComponent: 8, bytesPerRow: 0, space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
ctx.scaleBy(x: s, y: s); p.draw(with: .mediaBox, to: ctx)
let rep = NSBitmapImageRep(cgImage: ctx.makeImage()!)
try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: a[4]))
